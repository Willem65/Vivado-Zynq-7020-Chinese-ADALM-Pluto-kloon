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
