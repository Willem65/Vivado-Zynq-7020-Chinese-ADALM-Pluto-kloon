# Pluto-SDR IQ-afregeling en Installatie: I2S naar FM/HF (70 MHz - 6 GHz)

Deze handleiding beschrijft hoe je de software voor de Pluto-SDR instelt en gebruikt via een Python-GUI of handmatig via SSH.

---

## Voorbereiding van de SD-kaart

1. Schrijf de software-inhoud van het zip-bestand `SD-card-pluto-wuffum.zip` naar een micro-SD-kaart.
2. Plaats het SD-kaartje in de Pluto-SDR.

### Hardware-aansluitingen (JP5-connector)

Sluit de I2S-pinnen van de connector als volgt aan:

* **`i2s_in_bclk`**: Pin 18 op de JP5-connector
* **`i2s_in_lrclk`**: Pin 16 op de JP5-connector
* **`i2s_in_data`**: Pin 14 op de JP5-connector

> **Belangrijk:** Zorg ervoor dat de 3.3V-signalen met behulp van bijvoorbeeld een spanningsdeler worden teruggebracht naar **1.8V**.
> 
> 3,3V-signaal ── 1k ──┬── naar FPGA-ingang (1,8V)
                     │
                    1k2
                     │
                    GND
>
> 

---

## Methode A: Python GUI (Aanbevolen voor Windows)

Volg onderstaande stappen om de grafische interface te installeren en te starten:

1. **Installeer Python en pip** op je computer (indien nog niet aanwezig):
   ```bash
   curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
   python3 get-pip.py
   ```

2. **Installeer de vereiste Paramiko-module**:
   ```bash
   python -m pip install paramiko
   ```

3. **Start het Python-script**:
   ```bash
   python pluto-wuffum-IQ-afregeling.py
   ```

Hiermee open je de grafische interface waarmee je de Pluto-SDR kunt instellen, inclusief de frequentie en de IQ-afregeling.

---

## Methode B: Alternatief via SSH (PuTTY)

Wil je de Python-stappen liever overslaan? Dan kun je de instellingen ook direct handmatig configureren via SSH (bijvoorbeeld met PuTTY):

```bash
devmem 0x41200000 32 10000    # tone_offset (0 = normale audio, >0 = testtoon met deze offset)
devmem 0x41210000 32 0        # phase
devmem 0x41220000 32 16384    # gain_i (16384 = 1.0 in Q2.14)
devmem 0x41230000 32 16384    # gain_q

iio_attr -u ip:192.168.1.148 -c -o ad9361-phy altvoltage1 frequency 1285000000
