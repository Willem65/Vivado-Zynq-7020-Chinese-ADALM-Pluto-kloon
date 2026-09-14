# Vivado-Zynq-7020-Chinese-ADALM-Pluto-kloon
Vivado Pluto (Zynq-7020 kloon) — I2S naar SDR-uitgang project, komende van ISE WebPack 14.7 / Spartan-6


# Pluto (Zynq-7020 kloon) — I2S naar SDR-uitgang project

Vivado-leerproject op een Chinese ADALM-Pluto-kloon (Zynq-7020), waarbij een
bestaand Spartan-6/ISE I2S-ontwerp wordt overgezet naar Vivado, en uitgebreid
tot een volledige RX → upsample → filter → IQ-modulatie → TX-keten.

## Doel

- Vivado leren kennen, komende van ISE WebPack 14.7 / Spartan-6.
- Een I2S-ingangssignaal (192 kHz samplerate) verwerken en upsamplen naar
  384 kHz, met FIR-filtering en fase-naar-IQ-omzetting (quarter-wave LUT),
  en als I2S-uitgang wegschrijven.
- Op termijn: integratie met de AD9361/9363 IQ-modulator die al op het board
  aanwezig is.

## Hardware

- **Board**: Chinese ADALM-Pluto-kloon met Xilinx Zynq-7020 (`xc7z020clg400-2`)
  en een AD9361/AD9363.
- **Systeemklok**: 50 MHz kristal op pin **N18** (bank 34) — dit week af van de
  40 MHz die in het originele "Fishball" ISE/Vivado-referentieproject werd
  aangenomen; bevestigd via meting én zichtbaar op het PCB-kristal.
- **Baseband-header (J2/JP5, 20-pins)**: bevat twee I/O-banken op verschillende
  spanningen — zie tabel hieronder. Dit weekt af van de veelal 2.5V-aanname in
  generieke online Pluto-schematics.

## Bevestigde pin-mapping (JP5/J2-header)

Alle onderstaande pinnen zijn **experimenteel geverifieerd** met een
multimeter/oscilloscoop (niet alleen uit een schematic overgenomen — een
eerdere aanname bleek voor dit board niet te kloppen).

| JP5-pin | FPGA-pin | Bank | Spanning | Gebruikt voor |
|---|---|---|---|---|
| 1  | —   | —  | 5V (voeding)   | — |
| 2  | —   | —  | GND            | — |
| 3  | —   | —  | 3.3V (voeding) | — |
| 4  | G19 | 35 | 1.8V (LVCMOS18) | vrij / test geweest |
| 5  | —   | —  | 1.8V (voeding) | — |
| 6  | G20 | 35 | 1.8V (LVCMOS18) | i2s_reset |
| 7  | V10 | 13 | 3.3V (LVCMOS33) | I2S TX data |
| 8  | J18 | 35 | 1.8V (LVCMOS18) | i2s_in_lrclk |
| 9  | U9  | 13 | 3.3V (LVCMOS33) | vrij |
| 10 | H18 | 35 | 1.8V (LVCMOS18) | i2s_in_data |
| 11 | U10 | 13 | 3.3V (LVCMOS33) | I2S TX lrclk |
| 12 | H16 | 35 | 1.8V (LVCMOS18) | vrij / test geweest |
| 13 | T9  | 13 | 3.3V (LVCMOS33) | I2S TX bclk |
| 14 | H17 | 35 | 1.8V (LVCMOS18) | i2s_in_bclk |
| 15 | —   | —  | XTAL_VTC (vaste referentiefunctie) | **niet zelf aansturen** |
| 16 | L14 | 35 | 1.8V (LVCMOS18) | vrij / test geweest |
| 17 | —   | —  | PTT (vaste functie) | **niet zelf aansturen** |
| 18 | L15 | 35 | 1.8V (LVCMOS18) | vrij / test geweest |
| 19 | —   | —  | AD9361 SYNC (vaste functie) | **niet zelf aansturen** |
| 20 | —   | —  | GND | — |

> Pin 15, 17 en 19 zijn vermoedelijk verbonden met de VCTCXO-tuninglijn, een
> PTT-schakeling en de AD9361 sync-pin. Deze zijn **niet** met eigen logica
> getest om elektrisch conflict met bestaande schakelingen te voorkomen.

## Signaalketen (top.v)

```
i2s_in_bclk/lrclk/data (extern, 1.8V, bank 35)
        │
        ▼
     I2SRX  ──────────────► rx_sample[31:0], strobe (192 kHz)
        │
        ▼
   clk_wiz_1 (12.288 MHz → 24.576/49.152 MHz, exact ×2/×4)
        │
        ▼
   Upsampler (192 kHz → 384 kHz)
        │
        ▼
   FIR_Filter
        │
        ▼
   PHASEACCUMULATOR
        │
        ▼
   LUT90 (fase → I/Q, quarter-wave)
        │
        ▼
   FIR_IQ (frame-uitlijning, I- en Q-tak apart)
        │
        ▼
   I2STX ──► i2s_tx_bclk/lrclk/data (uitgang, 3.3V, bank 13)
```

`clk_wiz_0` (50 MHz → 12.288/24.576/49.152 MHz) was de eerste leeroefening in
Vivado's Clocking Wizard en zit nog in het project, maar wordt niet meer
gebruikt in de echte signaalketen — de outputs hangen bewust los.

## Belangrijkste lessen / valkuilen

- **Klokfrequentie niet aannemen, meten.** De originele XDC nam 40 MHz aan;
  het board bleek 50 MHz te hebben.
- **IOSTANDARD moet bij de fysieke VCCO passen.** Bank 35 bleek 1.8V te zijn,
  niet de aangenomen 2.5V — bevestigd door een output-pin op '1' te zetten en
  de spanning te meten (de fysieke VOH volgt altijd de echte VCCO, ongeacht
  wat er in de XDC gedeclareerd staat).
- **Niet elke pin is clock-capable.** Een externe BCLK op een niet-CC-pin
  (of de N-side van een differentieel paar) geeft een "IO Clock Placer
  failed"-fout; op te lossen met `CLOCK_DEDICATED_ROUTE FALSE` voor
  langzame kloksignalen.
- **Onbenutte top-level output-poorten mag je niet allemaal tegelijk laten
  hangen.** Eén poort zonder driver is onschuldig (wordt weggeoptimaliseerd),
  maar als *alle* paden naar een fysieke pin tegelijk wegvallen, optimaliseert
  Vivado de hele bijbehorende logica weg ("design is empty").
- **Test-signalen opruimen zodra hun doel bereikt is.** Meerdere generaties
  test-poorten (bijv. VCCO-meettests) die naast de echte functionele
  poorten blijven bestaan, leiden tot pin-tekort en "unplaced IO"-fouten.
- **Generieke online schematics voor Chinese boardklonen zijn niet
  betrouwbaar.** Zelfs P/N-toewijzing van differentiële pinnen bleek
  tegengesteld aan wat gangbare bronnen suggereerden — alleen Vivado's eigen
  DRC-melding (gebaseerd op de echte silicium-database) en eigen metingen
  gaven zekerheid.

## Projectstructuur

```
top.v              -- top-level module, instantieert alle blokken
I2SRX.v            -- I2S-ontvanger (overgenomen uit het Spartan-6 project)
Upsampler.v        -- 192 kHz -> 384 kHz
FIR_Filter.v        -- FIR-filter na upsampling
PHASEACCUMULATOR.v -- fase-accumulator voor IQ-modulatie
LUT90.v            -- quarter-wave lookup table, fase -> I/Q
FIR_IQ.v           -- FIR-filter + frame-uitlijning op I- en Q-tak
I2STX.v            -- I2S-uitgang
pluto_clock_test.xdc -- constraints (pin-toewijzing, klokken, IOSTANDARD)
```

## Openstaande punten / roadmap

- [ ] Bank 34 (N18, systeemklok) nog niet apart op VCCO gemeten.
- [ ] Nood-/fallback-klok bouwen voor als de externe I2S-BCLK wegvalt
      (was het oorspronkelijke doel van de Spartan-6 klok-switch-logica).
- [ ] Spanningsniveau-aanpassing (weerstandsdeler of actieve
      niveauvertaler) uitwerken voor de I2S RX-ingang als de externe bron
      op 3.3V zwaait.
- [ ] AD9361/9363-integratie (via ADI's `axi_ad9361`-referentie-IP).
- [ ] Zynq PS7 / IP Integrator block design verkennen.

## Licentie

Voeg hier je gewenste licentie toe (bijv. MIT, GPL-3.0).



# PlutoSDR: I2S/FM-synthese keten integreren in het officiële `pluto` HDL-project

## Doel

Een zelfgebouwde FPGA-keten (I2S-audio-ingang → upsampler → FIR-filter → phase accumulator → quarter-wave LUT → I/Q → FIR → I2S-uitgang, bedoeld voor FM-synthese) integreren in het officiële ADI `hdl/projects/pluto` project (Zynq 7020, ADALM-PLUTO / "Fishball"-kloon), zodat deze uiteindelijk data direct naar de interne AD9361-radiochip kan sturen in plaats van naar een externe AD8346 IQ-modulator.

Uiteindelijk resultaat: **werkend, reproduceerbaar firmware-image, succesvol getest op echte hardware (SD-boot), met hoorbaar audio-resultaat.**

---

## Belangrijkste inzicht vooraf

Twee bestaande designs werden gecombineerd:
- Een los I2S/FM-testproject (`top.v` + eigen XDC), dat oorspronkelijk naar externe pinnen / een externe AD8346 stuurde.
- Het officiële Pluto-project (`system_top.v`, `system_wrapper.bd` via `system_bd.tcl`), dat via `axi_ad9361` al rechtstreeks met de interne AD9361-radiochip praat (LVDS-lijnen `rx_data_in_*` / `tx_data_out_*`).

Je eigen logica toevoegen aan `system_top.v` is net zo simpel als een extra module-instantie toevoegen (zoals het bestaande `led_blinker`-voorbeeld al deed). De complexiteit zat 'm vrijwel volledig in: (1) pin-hergebruik-conflicten, (2) restanten van niet-gebruikte IP-blokken in het block design, en (3) reproduceerbaarheid van het hele buildsysteem.

---

## Problemen en oplossingen (chronologisch)

### 1. Pin-conflicten op de baseband-header (JP5)
Het I2S-testproject hergebruikte fysieke pinnen (`L14`, `L15`, `H17`, `V10`, `U9`, `U10`) die in het Pluto-project al bezet waren door de (ongebruikte) baseband-headerfunctionaliteit (`bb_in_ddr[0:5]`, `clk_to_bb`, `clk_to_sdr`, `IIC_0_0_*`, `gpio_bb_2`).

**Oplossing:** dezelfde fysieke pinnen hergebruiken voor de I2S-signalen, met de juiste `IOSTANDARD` (LVCMOS25/33 in plaats van de oorspronkelijke LVCMOS18), en de oude functienamen in de XDC vervangen door de nieuwe I2S-poortnamen.

### 2. "Multiple driver" / self-assign fout
```verilog
assign i2s_out_data384 = i2s_out_data384;  // overbodig en dubbele driver
```
**Oplossing:** verwijderd; de I2STX-instantie stuurt de poort al rechtstreeks aan.

### 3. MMCM/Clocking Wizard-fout na pin-ontkoppeling
```
[DRC REQP-123] The MMCME2_ADV with CLKINSEL tied high requires the CLKIN1 pin to be active.
```
Oorzaak: een *ander* (reeds in het block design aanwezig, niet door de gebruiker aangemaakt) Clocking Wizard-blok (`clk_wiz_0`) had zijn `clk_in1` verbonden met `clk_to_sdr` — een top-level poort die net was losgekoppeld. Dit blok, samen met `axi_bb_input_0`, was ooit handmatig via de GUI aan het block design toegevoegd en stond niet in `system_bd.tcl`.

**Oplossing:** `clk_wiz_0` én `axi_bb_input_0` volledig verwijderd uit het block design (canvas), gevalideerd, en de wrapper geregenereerd. *(Achteraf bleek dit sowieso nooit in een schone tcl-rebuild te zijn ontstaan — zie punt 7.)*

### 4. IOBUF-plaatsingsfouten voor IIC_0_0
Na het loskoppelen van `IIC_0_0_scl_io`/`sda_io` in `system_top.v` bleven de bijbehorende `IOBUF`-instanties in het (destijds nog geïmporteerde, statische) `system_wrapper.v`-bestand ongebruikt achter, zonder pin — "unplaced after IO placer".

**Oplossing:** de betreffende `IOBUF`-blokken en hun verbindingen handmatig uit dat specifieke gegenereerde bestand verwijderd.

### 5. Ontbrekende LR-klok op de I2S-uitgang
Bij het opschonen van een dubbele-driver-fout was per ongeluk ook de geldige `assign i2s_out_lrclk384 = i2s_out_lrclk;`-regel uitgecommentarieerd. Later opgelost door `I2STX` rechtstreeks aan de outputpoort te koppelen.

### 6. Burst-gedrag op de I2S LR-klok
Kortstondig waargenomen: pulsen in blokjes met stiltes ertussen — klassiek symptoom van een upsampler die zijn output-samples in een burst genereert in plaats van gelijkmatig verspreid. (Nog niet volledig uitgewerkt/opgelost in deze sessie — vervolgpunt voor later.)

### 7. Reproduceerbaarheid: IP-cores en block-design-wijzigingen "overleven" geen schone build
Grote les: dit project wordt bij elke schone build **vanaf nul** opgebouwd via `system_project.tcl` (bronbestanden) en `system_bd.tcl` (block design). Handmatige aanpassingen die alleen in de Vivado-GUI of in automatisch gegenereerde bestanden (`system_wrapper.v`) zijn gedaan, verdwijnen bij een schone rebuild (`make clean && make`, of buildroot vanaf een verse checkout).

**Concrete acties om dit blijvend te maken:**
- Eigen Clocking Wizard (`clk_wiz_i2s`) toegevoegd als `.xci`-bestand in de projectmap, en geregistreerd in:
  - `system_project.tcl` → toegevoegd aan de `adi_project_files`-lijst.
  - `Makefile` (project-niveau) → `M_DEPS += clk_wiz_i2s.xci` geactiveerd.
- Bevestigd via `grep` dat `axi_bb_input_0`/`clk_wiz_0`/`bb_in_ddr`/`clk_to_sdr`/`IIC_0_0` **niet** voorkomen in `system_bd.tcl` — dus een schone build maakt deze blokken sowieso nooit aan. Geen verdere tcl-aanpassing nodig voor dit punt.
- Geverifieerd met een volledig schone rebuild (`rm -rf pluto.cache pluto.gen pluto.hw pluto.ip_user_files pluto.runs pluto.srcs pluto.xpr .Xil ADIIGNOREVERSIONCHECK1 && make -C hdl/projects/pluto`).

### 8. Timing closure faalde bij command-line build (maar niet in de GUI)
```
WNS = -6.700 ns, TNS = -26039.340 ns, 4568 falende eindpunten
```
De Vivado GUI accepteert een bitstream ook als timing niet gehaald wordt (alleen een waarschuwing); het `adi_project_impl`-buildscript van ADI keurt de build in dat geval bewust **hard af**. Root cause, zichtbaar in de "Inter Clock Table":
```
sys_clk_pin  →  clk_out1_clk_wiz_i2s   WNS=-5.728, TNS=-224.438
sys_clk_pin  →  clk_out2_clk_wiz_i2s   WNS=-6.700, TNS=-25814.902
```
Een reset-signaal (`i2s_reset`, gegenereerd in het `clk_in1`/`sys_clk_pin`-domein) werd gebruikt in de volledig ongerelateerde `clk_wiz_i2s`-uitgangsklokdomeinen, zonder dat deze twee klokgroepen als asynchroon waren gedeclareerd.

**Oplossing — toegevoegd aan `system_constr.xdc`:**
```tcl
set_clock_groups -asynchronous \
  -group [get_clocks sys_clk_pin] \
  -group [get_clocks -include_generated_clocks {clk_out1_clk_wiz_i2s clk_out2_clk_wiz_i2s}]
```
Resultaat: schone build met **0 errors**, timing gehaald.

### 9. Hoofdbuildsysteem (buildroot/Linux/u-boot) — download-fallback i.p.v. lokale HDL-build
```
wget ... plutosdr-fw/releases/download/v0.5.2/system_top.xsa
HTTP request sent, awaiting response... 404 Not Found
make: *** [Makefile:148: build/system_top.xsa] Error 8
```
Het hoofd-`Makefile` van de firmware-repository (`fish-wan-plutosdr-fw-7020-sdr`) detecteert zelf of een werkende Vivado-installatie beschikbaar is (`HAVE_VIVADO`). Zo ja: het bouwt de HDL lokaal en kopieert het resultaat automatisch. Zo nee: het valt terug op het downloaden van een kant-en-klare release — die download faalde (verouderde/niet-bestaande release-asset).

Er werd eerst geprobeerd dit handmatig te omzeilen (`mkdir build` + handmatig kopiëren van de `.xsa`), wat **niet betrouwbaar bleek** zolang de Vivado-detectie zelf niet klopte — de download-poging bleef terugkomen zodra `make` opnieuw werd aangeroepen.

**De uiteindelijke, werkende oplossing:**
```bash
cd ~/work/fish-wan-plutosdr-fw-7020-sdr
source ~/tools/Xilinx/Vitis/2022.2/settings64.sh
make VIVADO_SETTINGS=~/tools/Xilinx/Vivado/2022.2/settings64.sh VIVADO_VERSION=v2022.2
```
Door `VIVADO_SETTINGS` (en `VIVADO_VERSION`) **rechtstreeks als `make`-commandoregel-variabele** mee te geven — in plaats van als losse `export` in een voorafgaande shell-sessie — detecteerde het Makefile zelf correct dat Vivado beschikbaar was, bouwde het de HDL lokaal (`make -C hdl/projects/pluto`), en kopieerde het de resulterende `.xsa` automatisch naar `build/`. Geen handmatige kopieerstappen meer nodig. Het eerder `source`n van de Vitis-settings zorgde voor de juiste cross-compiler-tools in `PATH` voor de Linux-kernel/u-boot-bouwstappen.

*(Achteraf-inzicht: het handmatig aanmaken van de `build/`-map bleek niet de eigenlijke sleutel tot de oplossing te zijn geweest — dat gebeurt sowieso automatisch door `make` zelf. De daadwerkelijke oorzaak was steeds de onbetrouwbare `VIVADO_SETTINGS`-detectie in losse terminalsessies.)*

Exit-code na deze aanroep: **0** — volledige, schone build geslaagd, inclusief Linux-kernel, u-boot, buildroot-rootfs.

### 10. SD-boot-image gebouwd en getest op hardware
```bash
make sdimg VIVADO_SETTINGS=~/tools/Xilinx/Vivado/2022.2/settings64.sh VIVADO_VERSION=v2022.2
```
Produceert `build_sdimg/` met `BOOT.bin`, `uImage`, `devicetree.dtb`, `uramdisk.image.gz`, `uEnv.txt` (de submap `bootbin/` bevat losse, ongecombineerde onderdelen voor JTAG-gebruik, niet nodig voor SD-boot). Op SD-kaart gezet, board in SD-boot-mode gezet — **werkt, met hoorbaar audio-resultaat.**

---

## Openstaande punten voor een volgende sessie

- Burst-gedrag in de Upsampler-output nader onderzoeken en verhelpen (zie punt 6).
- De uiteindelijke architectuurvraag: I/Q-data rechtstreeks (fabric-direct, zonder DMA/PS) naar de `axi_ad9361`-DAC-user-poorten sturen (`dac_data_i0`/`q0`, `dac_valid_i0`, `dac_enable_i0`) in plaats van via I2S naar een externe AD8346. **Belangrijke ontdekking:** dit project heeft in `system_bd.tcl` al een werkend voorbeeld van precies dit pad (een DDS-compiler die rechtstreeks op `dac_data_i0`/`q0` is aangesloten) — bruikbaar als referentie.
- Voor bredere signalen (analoge video, NICAM 728): een aparte, breedbandige generatorketen nodig op (een deler van) de DAC-sampleklok `l_clk`, los van het huidige 49.152 MHz audio-domein, met een FIFO ertussen voor de klokdomeinovergang.
- CDC-synchronisatie van `i2s_reset` zelf (nu direct gebruikt in meerdere klokdomeinen) nog niet met een `sync_bits`-synchronizer afgehandeld — timing-technisch nu opgelost via `set_clock_groups`, maar functioneel netter met een echte synchronizer.

---

*Samengevat vanuit een troubleshooting-sessie met Claude (Anthropic).*

