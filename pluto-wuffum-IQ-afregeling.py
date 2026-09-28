#!/usr/bin/env python3
"""
pluto_iq_gui.py - schuifregelaars voor IQ-correctie op de Pluto.

Werking: een SSH-verbinding naar de Pluto; elke wijziging wordt daar uitgevoerd als
  devmem <adres> 32 <waarde>          (eigen FPGA-registers)
  iio_attr ...                        (AD9361-instellingen)

Installatie op de host:
  Linux:   sudo apt install python3-tk ; pip install paramiko
  Windows: pip install paramiko        (tkinter zit bij Python)

Instellingen (IP, wachtwoord, alle sliders, LO) staan in pluto_iq_settings.json naast dit script
en worden automatisch opgeslagen en bij de volgende start weer ingelezen.

Start:  python3 pluto_iq_gui.py            (echt)
        python3 pluto_iq_gui.py --dry-run  (alleen commando's tonen, geen verbinding)
"""
import json
import math
import os
import queue
import sys
import threading

# --------------------------------------------------------------------------
# Registerkaart (zie Address Editor in Vivado)
# --------------------------------------------------------------------------
REGS = {
    # naam: (adres, min, max, standaard, omschrijving)
    "tone_offset": (0x41200000, 0, 30000, 0,     "Testtoon-offset (0 = normale audio)"),
    "phase":       (0x41210000, -3000, 3000, 0,  "Fasecorrectie sin(phi), Q2.14"),
    "gain_i":      (0x41220000, 10000, 22000, 16384, "I-versterking, Q2.14 (16384 = 1.0)"),
    "gain_q":      (0x41230000, 10000, 22000, 16384, "Q-versterking, Q2.14 (16384 = 1.0)"),
    "dc_i":        (0x41240000, -4000, 4000, 0,  "I DC-offset"),
    "dc_q":        (0x41250000, -4000, 4000, 0,  "Q DC-offset"),
}

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pluto_iq_settings.json")

DEFAULT_SETTINGS = {
    "connection": {"host": "192.168.1.148", "user": "root", "password": "analog", "auto_connect": False},
    "registers": {n: v[3] for n, v in REGS.items()},
    "ad9361": {"tx_gain": -40, "calib_scale_i": 0, "calib_scale_q": 0, "calib_phase_q": 0, "tx_lo_mhz": "100.0"},
}

IIO_RANGES = {"tx_gain": (-359, 0), "calib_scale_i": (-100, 100),
              "calib_scale_q": (-100, 100), "calib_phase_q": (-100, 100)}


def _clamp(v, lo, hi):
    return max(lo, min(hi, int(v)))


def load_settings(path=SETTINGS_FILE):
    """Leest de JSON; ontbrekende of ongeldige velden vallen terug op de standaardwaarden."""
    import copy
    s = copy.deepcopy(DEFAULT_SETTINGS)
    try:
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("geen object")
    except FileNotFoundError:
        return s
    except (ValueError, OSError):
        try:  # kapot bestand bewaren i.p.v. stilletjes overschrijven
            os.replace(path, path + ".bad")
        except OSError:
            pass
        return s
    conn = data.get("connection", {})
    for k in ("host", "user", "password"):
        if isinstance(conn.get(k), str):
            s["connection"][k] = conn[k]
    if isinstance(conn.get("auto_connect"), bool):
        s["connection"]["auto_connect"] = conn["auto_connect"]
    for n, (_, lo, hi, _, _) in REGS.items():
        try:
            s["registers"][n] = _clamp(data.get("registers", {})[n], lo, hi)
        except (KeyError, TypeError, ValueError):
            pass
    for n, (lo, hi) in IIO_RANGES.items():
        try:
            s["ad9361"][n] = _clamp(data.get("ad9361", {})[n], lo, hi)
        except (KeyError, TypeError, ValueError):
            pass
    try:
        s["ad9361"]["tx_lo_mhz"] = str(float(data.get("ad9361", {})["tx_lo_mhz"]))
    except (KeyError, TypeError, ValueError):
        pass
    return s


def save_settings(settings, path=SETTINGS_FILE):
    """Schrijft atomair (eerst tijdelijk bestand, dan vervangen)."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(settings, f, indent=2)
    os.replace(tmp, path)


def reg_command(name, value):
    """devmem-commando voor een 16-bit signed waarde (two's complement, 32-bit woord)."""
    addr = REGS[name][0]
    return "devmem 0x%08X 32 0x%04X" % (addr, int(value) & 0xFFFF)


def iio_command(dev, chan, attr, value, output=True):
    flag = "-c -o" if output else "-c"
    return "iio_attr %s %s %s %s %s" % (flag, dev, chan, attr, value)


def iio_device_command(dev, attr, value):
    return "iio_attr -d %s %s %s" % (dev, attr, value)


def phase_degrees(v):
    x = max(-1.0, min(1.0, v / 16384.0))
    return math.degrees(math.asin(x))


# --------------------------------------------------------------------------
# Transport: SSH of dry-run
# --------------------------------------------------------------------------
class DryRunTransport:
    def __init__(self, log):
        self.log = log

    def connect(self, host, user, password):
        self.log("[dry-run] verbonden met %s" % host)

    def run(self, cmd):
        self.log("[dry-run] %s" % cmd)
        return ""

    def close(self):
        pass


class SSHTransport:
    def __init__(self, log):
        self.log = log
        self.client = None

    def connect(self, host, user, password):
        import paramiko
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(host, username=user, password=password,
                            look_for_keys=False, allow_agent=False, timeout=5)

    def run(self, cmd):
        _, out, err = self.client.exec_command(cmd, timeout=10)
        o = out.read().decode(errors="replace").strip()
        e = err.read().decode(errors="replace").strip()
        if e:
            self.log("FOUT bij '%s': %s" % (cmd, e))
        return o

    def close(self):
        if self.client:
            self.client.close()
            self.client = None


class Sender(threading.Thread):
    """Voert commando's uit op een achtergrondthread; per sleutel telt alleen de laatste waarde."""

    def __init__(self, transport, log):
        super().__init__(daemon=True)
        self.transport = transport
        self.log = log
        self.pending = {}
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.running = True

    def submit(self, key, cmd):
        with self.lock:
            self.pending[key] = cmd
        self.wake.set()

    def run(self):
        while self.running:
            self.wake.wait(0.5)
            self.wake.clear()
            with self.lock:
                batch = list(self.pending.items())
                self.pending.clear()
            for _, cmd in batch:
                try:
                    self.transport.run(cmd)
                except Exception as exc:  # netwerk weggevallen e.d.
                    self.log("FOUT: %s" % exc)


# --------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------
def build_gui(dry_run=False):
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("Pluto IQ-afregeling")

    logbox = tk.Text(root, height=6, width=80, state="disabled")

    log_queue = queue.Queue()

    def log(msg):
        """Thread-veilig: alleen in de wachtrij zetten; de hoofdthread schrijft het naar het venster."""
        log_queue.put(msg)

    def poll_log():
        try:
            while True:
                msg = log_queue.get_nowait()
                logbox.configure(state="normal")
                logbox.insert("end", msg + "\n")
                logbox.see("end")
                logbox.configure(state="disabled")
        except queue.Empty:
            pass
        except tk.TclError:
            return  # venster gesloten
        root.after(100, poll_log)

    root.after(100, poll_log)

    transport = DryRunTransport(log) if dry_run else SSHTransport(log)
    state = {"sender": None}

    # ---- verbinding ----
    top = ttk.Frame(root, padding=6)
    top.grid(row=0, column=0, sticky="ew")
    cfg = load_settings()
    host_var = tk.StringVar(value=cfg["connection"]["host"])
    user_var = tk.StringVar(value=cfg["connection"]["user"])
    pass_var = tk.StringVar(value=cfg["connection"]["password"])
    auto_var = tk.BooleanVar(value=cfg["connection"]["auto_connect"])
    for i, (lab, var, show) in enumerate([("IP", host_var, None), ("gebruiker", user_var, None),
                                          ("wachtwoord", pass_var, "*")]):
        ttk.Label(top, text=lab).grid(row=0, column=2 * i, padx=2)
        ttk.Entry(top, textvariable=var, width=16, show=show).grid(row=0, column=2 * i + 1, padx=2)
    status = ttk.Label(top, text="niet verbonden", foreground="red")
    status.grid(row=0, column=7, padx=8)
    ttk.Checkbutton(top, text="auto-verbinden bij start", variable=auto_var).grid(row=1, column=0, columnspan=4, sticky="w")

    save_job = {"id": None}

    def collect():
        return {
            "connection": {"host": host_var.get(), "user": user_var.get(),
                           "password": pass_var.get(), "auto_connect": auto_var.get()},
            "registers": {n: sliders[n]["var"].get() for n in REGS},
            "ad9361": dict({n: iio_sliders[n]["var"].get() for n in IIO_RANGES},
                           tx_lo_mhz=lo_var.get()),
        }

    def save_now():
        save_job["id"] = None
        try:
            save_settings(collect())
        except (OSError, tk.TclError, NameError) as exc:
            log("Opslaan mislukt: %s" % exc)

    def schedule_save(*_):
        if save_job["id"] is not None:
            root.after_cancel(save_job["id"])
        save_job["id"] = root.after(500, save_now)

    for v in (host_var, user_var, pass_var, auto_var):
        v.trace_add("write", schedule_save)

    sliders = {}

    def send_reg(name):
        s = state["sender"]
        if s:
            s.submit("reg:" + name, reg_command(name, sliders[name]["var"].get()))

    def apply_all():
        for n in REGS:
            send_reg(n)
        send_iio_all()

    def connect():
        try:
            transport.connect(host_var.get(), user_var.get(), pass_var.get())
        except Exception as exc:
            status.configure(text="mislukt", foreground="red")
            log("Verbinden mislukt: %s" % exc)
            return
        sender = Sender(transport, log)
        sender.start()
        state["sender"] = sender
        status.configure(text="verbonden", foreground="green")
        log("Verbonden. Huidige sliderwaarden worden naar de Pluto gestuurd.")
        apply_all()   # registers staan na een reboot op 0 (gain = 0 => geen signaal!)

    ttk.Button(top, text="Verbinden", command=connect).grid(row=0, column=6, padx=4)

    # ---- IQ-registers ----
    frame = ttk.LabelFrame(root, text="IQ-correctie (FPGA-registers)", padding=6)
    frame.grid(row=1, column=0, sticky="ew", padx=6, pady=4)

    def make_slider(parent, row, name, lo, hi, default, descr, on_change, fmt=None):
        var = tk.IntVar(value=default)
        ttk.Label(parent, text=name, width=12).grid(row=row, column=0, sticky="w")
        val_lab = ttk.Label(parent, width=22)

        def changed(_=None):
            v = var.get()
            val_lab.configure(text=fmt(v) if fmt else str(v))
            on_change(name)
            schedule_save()

        scale = tk.Scale(parent, from_=lo, to=hi, orient="horizontal", length=420,
                         variable=var, showvalue=False, command=changed)
        scale.grid(row=row, column=1, padx=4)

        def step(d):
            var.set(max(lo, min(hi, var.get() + d)))
            changed()

        ttk.Button(parent, text="-", width=2, command=lambda: step(-1)).grid(row=row, column=2)
        ttk.Button(parent, text="+", width=2, command=lambda: step(+1)).grid(row=row, column=3)
        val_lab.grid(row=row, column=4, padx=6, sticky="w")
        ttk.Label(parent, text=descr).grid(row=row, column=5, sticky="w")
        val_lab.configure(text=fmt(default) if fmt else str(default))
        return {"var": var, "scale": scale, "changed": changed}

    def fmt_for(name):
        if name in ("gain_i", "gain_q"):
            return lambda v: "%d  (%.3f)" % (v, v / 16384.0)
        if name == "phase":
            return lambda v: "%d  (%.2f graden)" % (v, phase_degrees(v))
        return None

    for r, (name, (addr, lo, hi, default, descr)) in enumerate(REGS.items()):
        sliders[name] = make_slider(frame, r, name, lo, hi, cfg["registers"][name], descr, send_reg, fmt_for(name))

    # ---- AD9361 via iio_attr ----
    frame2 = ttk.LabelFrame(root, text="AD9361 (iio_attr)", padding=6)
    frame2.grid(row=2, column=0, sticky="ew", padx=6, pady=4)
    iio_sliders = {}

    def send_iio(name):
        s = state["sender"]
        if not s:
            return
        v = iio_sliders[name]["var"].get()
        if name == "tx_gain":
            cmd = iio_command("ad9361-phy", "voltage0", "hardwaregain", "%.2f" % (v / 4.0))
        elif name == "calib_scale_i":
            cmd = iio_command("cf-ad9361-dds-core-lpc", "voltage0", "calibscale", "%.4f" % (1 + v / 1000.0))
        elif name == "calib_scale_q":
            cmd = iio_command("cf-ad9361-dds-core-lpc", "voltage1", "calibscale", "%.4f" % (1 + v / 1000.0))
        elif name == "calib_phase_q":
            cmd = iio_command("cf-ad9361-dds-core-lpc", "voltage1", "calibphase", "%.4f" % (v / 1000.0))
        else:
            return
        s.submit("iio:" + name, cmd)

    def send_iio_all():
        for n in iio_sliders:
            send_iio(n)
        try:
            set_lo()
        except (ValueError, NameError):
            log("LO-frequentie ongeldig, niet ingesteld.")

    specs = [
        ("tx_gain", -359, 0, -40, "TX-gain (dB): waarde/4, -89.75..0",
         lambda v: "%.2f dB" % (v / 4.0)),
        ("calib_scale_i", -100, 100, 0, "calibscale I: 1 + waarde/1000",
         lambda v: "%.3f" % (1 + v / 1000.0)),
        ("calib_scale_q", -100, 100, 0, "calibscale Q: 1 + waarde/1000",
         lambda v: "%.3f" % (1 + v / 1000.0)),
        ("calib_phase_q", -100, 100, 0, "calibphase Q: waarde/1000 (eenheid onbevestigd, klein beginnen)",
         lambda v: "%.3f" % (v / 1000.0)),
    ]
    for r, (name, lo, hi, default, descr, fmt) in enumerate(specs):
        iio_sliders[name] = make_slider(frame2, r, name, lo, hi, cfg["ad9361"][name], descr, send_iio, fmt)

    # LO-frequentie en kalibratie
    row = len(specs)
    lo_var = tk.StringVar(value=cfg["ad9361"]["tx_lo_mhz"])
    lo_var.trace_add("write", schedule_save)
    ttk.Label(frame2, text="TX-LO (MHz)").grid(row=row, column=0, sticky="w")
    ttk.Entry(frame2, textvariable=lo_var, width=12).grid(row=row, column=1, sticky="w")

    def set_lo():
        s = state["sender"]
        if s:
            hz = int(float(lo_var.get()) * 1e6)
            s.submit("iio:lo", iio_command("ad9361-phy", "altvoltage1", "frequency", hz))

    def calib(mode):
        s = state["sender"]
        if s:
            s.submit("iio:calib", iio_device_command("ad9361-phy", "calib_mode", mode))

    ttk.Button(frame2, text="Zet LO", command=set_lo).grid(row=row, column=2, columnspan=2)
    ttk.Button(frame2, text="tx_quad kalibratie", command=lambda: calib("tx_quad")).grid(row=row, column=4, sticky="w")
    ttk.Button(frame2, text="rf_dc_offs kalibratie", command=lambda: calib("rf_dc_offs")).grid(row=row, column=5, sticky="w")

    # ---- knoppen ----
    btns = ttk.Frame(root, padding=6)
    btns.grid(row=3, column=0, sticky="ew")

    def reset_neutral():
        for n, (_, _, _, d, _) in REGS.items():
            sliders[n]["var"].set(d)
            sliders[n]["changed"]()

    def tone_toggle():
        v = sliders["tone_offset"]["var"]
        v.set(10000 if v.get() == 0 else 0)
        sliders["tone_offset"]["changed"]()

    ttk.Button(btns, text="Neutraal (reset)", command=reset_neutral).grid(row=0, column=0, padx=4)
    ttk.Button(btns, text="Testtoon aan/uit", command=tone_toggle).grid(row=0, column=1, padx=4)
    ttk.Label(btns, text="Instellingen worden automatisch opgeslagen in " + os.path.basename(SETTINGS_FILE)).grid(row=0, column=2, padx=8)

    logbox.grid(row=4, column=0, padx=6, pady=6)

    def on_close():
        save_now()
        if state["sender"]:
            state["sender"].running = False
        transport.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    if auto_var.get():
        root.after(300, connect)
    return root


if __name__ == "__main__":
    build_gui(dry_run="--dry-run" in sys.argv).mainloop()
