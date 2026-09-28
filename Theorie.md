# I²S en de Fase-Accumulator (DDS)

Aantekeningen over digitale audio via I²S en het opwekken van een sinus met een fase-accumulator en een LUT (Look-Up Table).

---

## Deel 1 — I²S

### 1.1 Sample-rate bepaalt de hoogste audiofrequentie

Volgens Shannon-Nyquist is de hoogst bruikbare audiofrequentie de helft van de sample-rate:

$$
f_{max} = \frac{f_s}{2}
$$

| Sample-rate | Hoogste audiofrequentie (theoretisch) |
|---|---|
| 48 kHz | 24 kHz |
| 192 kHz | 96 kHz |
| 384 kHz | 192 kHz |

> In de praktijk ligt de bruikbare grens iets lager, omdat het reconstructiefilter van de DAC een overgangsgebied nodig heeft.

### 1.2 De bit clock (BCLK)

Elke sample is een getal (bijv. 16 bits) dat de **amplitude** van het audiosignaal op dat moment voorstelt. Per sample-periode (één LRCLK-cyclus, één *frame*) moeten de bits van **beide kanalen** verstuurd worden: eerst links, dan rechts.

$$
BCLK = f_s \times \text{bits per kanaal-slot} \times \text{aantal kanalen}
$$

| Sample-rate | Bits per slot | Kanalen | Bits per frame | Bit clock |
|---|---|---|---|---|
| 192 kHz | 16 | 2 | 32 | (16+16) × 192 kHz = **6,144 MHz** |
| 192 kHz | 32 | 2 | 64 | (32+32) × 192 kHz = **12,288 MHz** |
| 384 kHz | 32 | 2 | 64 | (32+32) × 384 kHz = **24,576 MHz** |

Tegenwoordig gebruikt vrijwel alle I²S-hardware **32-bit slots**: 32 bits terwijl LRCLK laag is (links) en 32 bits terwijl LRCLK hoog is (rechts), samen 64 bits per frame. Vaak worden daarvan toch maar de bovenste 16 (of 24) bits echt gebruikt; de rest is nul. Omdat de data MSB-first wordt verstuurd, maakt dat voor de ontvanger niet uit.

**Samengevat — wat verhoogt de bit clock?**

| Wijziging | Effect |
|---|---|
| Sample-rate omhoog | Bit clock omhoog, hogere maximale audiofrequentie (meer punten per seconde) |
| Aantal bits omhoog | Bit clock omhoog, nauwkeurigere amplitude (fijnere verticale resolutie) |
| Meer kanalen | Bit clock omhoog |

### 1.3 De één-bit vertraging

I²S is "één clockbit vertraagd" geklokt. Dat is historisch gegroeid:

- **WS (LRCLK)** verandert één BCLK-cyclus **vóór** de MSB.
- Data wordt **gelezen** op de **opgaande** flank van BCLK.
- Data **verandert** op de **neergaande** flank van BCLK.

In de begintijd van digitale audio (Philips) werden schuifregisters gebruikt. De hardware kreeg zo precies één BCLK-cyclus de tijd om de interne registers te *latchen* (vast te zetten) voordat de eerste echte bit van het nieuwe kanaal binnenkomt.

```
BCLK-cyclus :  n-1       n         n+1       n+2      ...
WS          :  hoog (R)  laag (L)  laag (L)  laag (L)
SD          :  R bit 1   R LSB     L MSB     L bit 30 ...
                         ^         ^
                         |         └─ eerste bit van het linker kanaal
                         └─ WS wisselt al, maar de laatste bit van R loopt nog
```

### 1.4 Nyquist binnen het I²S-frame

Om een sinus op de allerhoogste frequentie (de Nyquist-frequentie) te reproduceren zijn **per kanaal minimaal 2 samples per periode** nodig: één positief en één negatief punt. Dat betekent **twee volledige LRCLK-cycli**.

Omdat elk frame achtereenvolgens links en rechts bevat, ziet de seriële datastroom er dan zo uit:

| Frame | Links | Rechts |
|---|---|---|
| 1 | + (positief punt) | + (positief punt) |
| 2 | − (negatief punt) | − (negatief punt) |

In de datastroom zie je dus eerst twee positieve "bulten" en daarna twee negatieve.

> **Let op:** links en rechts in hetzelfde frame horen bij **hetzelfde tijdstip**. Ze worden na elkaar verstuurd, maar de DAC zet ze tegelijk om. Het zijn dus 2 momenten in de tijd (met elk een L- en R-waarde), niet 4.
>
> Precies op Nyquist hangt het resultaat ook af van de fase: vallen de samples op de nuldoorgangen, dan zijn ze allemaal nul. Daarom blijf je in de praktijk ruim onder f_s / 2.

---

## Deel 2 — De fase-accumulator

### 2.1 Het principe

De fase-accumulator is de **motor** die bepaalt hoe snel je door de LUT loopt. In de LUT staan de punten van één periode met de bijbehorende amplitude; de tabel bepaalt dus de **vorm** van het signaal (in ons geval een sinus).

- De **stapgrootte** (Phase Increment, *M*) is het **gaspedaal**.
- Het gaspedaal wordt bediend door de **modulatie**.
- Bij elke sample wordt *M* bij de accumulator opgeteld; de bovenste bits van de accumulator vormen het adres in de LUT.

```
            +------------------+      bovenste bits     +-------+
  M  ---->  | accumulator (N)  | ---------------------> |  LUT  | ---> sample naar I²S
            +------------------+                        +-------+
                 ^         |
                 +---------+   elke sample: acc = acc + M
```

### 2.2 De uitgangsfrequentie

$$
f_{out} = \frac{M \cdot f_s}{2^N}
\qquad\Longleftrightarrow\qquad
M = \frac{f_{out} \cdot 2^N}{f_s}
$$

| Symbool | Betekenis |
|---|---|
| f_out | de gewenste audiofrequentie |
| M | de Phase Increment (stapgrootte) |
| f_s | de sample-rate (bijv. 192 kHz) |
| 2^N | het bereik van de accumulator (bijv. 2³² voor een 32-bit teller) |

**Voorbeeld:** 1 kHz bij f_s = 192 kHz en N = 32:

$$
M = \frac{1000 \cdot 4\,294\,967\,296}{192\,000} \approx 22\,369\,621
$$

### 2.3 De laagste frequentie

Met M = 1 duurt één rondje 2³² = 4 294 967 296 samples:

$$
f_{min} = \frac{192\,000}{4\,294\,967\,296} \approx 0{,}0000447\ \text{Hz}
$$

Dat is één trilling per ongeveer **6,2 uur**. Dit is meteen ook de **frequentieresolutie**: elke stap van M verschuift de toon met 0,0000447 Hz. De laagste frequentie is dus altijd "laag genoeg".

---

## Deel 3 — De LUT (Look-Up Table)

### 3.1 Hoeveel trapjes mag mijn sinus hebben?

De tabel bepaalt de **zuiverheid** van de sinus.

- **Weinig punten (bijv. 2 of 4):** ga je heel langzaam door de tabel, dan blijft de uitgang lang "hoog" en daarna lang "laag". Je krijgt een blokgolf, vol met harmonischen (bijgeluiden) die je in een zuivere sinus niet wilt.
- **Veel punten (hier: 16 384 × 4 kwadranten):** bij lage tonen verandert de waarde bij bijna elke stap van de accumulator een heel klein beetje. De trapjes zijn zo klein dat ze na het filter van de DAC onzichtbaar zijn.

### 3.2 Kwart-sinus tabel

Er wordt maar een **kwart sinus** opgeslagen (16 384 punten). Door symmetrie volgt daar een hele periode van 65 536 punten uit. Van de bovenste 16 bits van de accumulator kiezen de 2 hoogste bits het kwadrant en de overige 14 bits de index:

| Kwadrant | Bovenste 2 bits | Tabel lezen | Teken |
|---|---|---|---|
| 0 (0°–90°) | `00` | vooruit: `index` | + |
| 1 (90°–180°) | `01` | gespiegeld: `16383 − index` | + |
| 2 (180°–270°) | `10` | vooruit: `index` | − |
| 3 (270°–360°) | `11` | gespiegeld: `16383 − index` | − |

### 3.3 Kwaliteit: SNR en THD

Bij het ontwerpen van de LUT kijk je vooral naar de **Signal-to-Noise Ratio (SNR)** en de **Total Harmonic Distortion (THD)**.

| Eigenschap | Bepaalt | Waarde in dit ontwerp |
|---|---|---|
| **Bit-diepte** (16 bit) | verticale nauwkeurigheid (amplitude) | ≈ 96–98 dB dynamiek, CD-kwaliteit |
| **Aantal adressen** (16 384 per kwart = 65 536 per periode) | horizontale nauwkeurigheid (fase) | weinig fase-ruis, extreem schone sinus |

> Vuistregel voor fase-afkapping: de stoorcomponenten liggen ongeveer 6 dB per fase-adresbit onder het signaal. 16 adresbits voor een hele periode geeft ≈ 96 dB, precies in balans met de 16-bit amplitude. Horizontale en verticale fout zijn dus even groot: een evenwichtig ontwerp.

### 3.4 De vuistregel

Bij het ontwerpen van een tabel wil je dat de fout door de "trapjes" (horizontaal én verticaal) **kleiner is dan wat de rest van het systeem kan weergeven**.

- Voor 16-bit audio is een tabel van 1024 of 2048 punten vaak al genoeg om een "schone" sinus te horen.
- 16 384 punten per kwart is "overkill" op een goede manier: laboratorium-waardige precisie. Zelfs bij de laagste frequentie blijft het een vloeiende lijn.

---

## Samenvatting

- **Sample-rate** bepaalt de hoogste frequentie (f_s / 2) en samen met bits en kanalen de **bit clock**.
- **I²S** gebruikt tegenwoordig 32-bit slots (64 bits per stereo-frame) met één bit vertraging na de WS-wissel.
- De **fase-accumulator** (32 bit) geeft een frequentieresolutie van ≈ 0,00004 Hz: de laagste frequentie is nooit een probleem.
- De **grote LUT** zorgt ervoor dat die lage frequenties ook echt als een sinus klinken, en niet als een blokgolf.
