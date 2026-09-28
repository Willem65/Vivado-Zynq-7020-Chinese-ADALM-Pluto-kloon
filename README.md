# Overzicht: een digitaal FM/MPX-stereosignaal opwekken via de AD9361 IQ-chip op een chinees pluto bordje Zynq7020

Dit document legt het **grote plaatje** uit van het project: hoe je van een gewoon audiosignaal (links/rechts) komt tot een echt, uitzendbaar FM-radiosignaal met stereo, volledig digitaal opgewekt in een FPGA, zonder externe modulator. De andere documenten in deze reeks gaan over de technische deelstappen en de problemen die onderweg zijn opgelost; dit document legt uit **waarom** die stappen er zijn en hoe ze samenhangen.

## Wat is een FM/MPX-stereosignaal eigenlijk?

Een gewone FM-radiozender zendt niet zomaar "links en rechts" apart uit. In plaats daarvan wordt er eerst een samengesteld basisbandsignaal gemaakt, het **MPX-signaal** (multiplex), dat bestaat uit:

- De **som** van links en rechts (L+R) — dit is het signaal dat een mono-ontvanger gewoon hoort.
- Een **19 kHz-piloottoon** — een vast, zuiver signaal waarmee een stereo-ontvanger herkent dat er stereo-informatie aanwezig is.
- Het **verschil** tussen links en rechts (L-R), gemoduleerd op een 38 kHz-subdraaggolf (het dubbele van de piloottoon) — dit bevat de stereo-informatie.
- Optioneel **RDS** (Radio Data System), een klein datasignaal op 57 kHz (3× de piloottoon) met tekstinformatie zoals zendernaam en songtitel.

Al deze onderdelen samen vormen één elektrisch signaal van ongeveer 0-60 kHz breed. Dát signaal wordt vervolgens gebruikt om de frequentie van de FM-draaggolf te laten variëren — dat is wat "FM" (frequentiemodulatie) betekent: hoe sterker het MPX-signaal op een bepaald moment, hoe verder de draaggolf-frequentie op dat moment afwijkt van zijn middenwaarde.

## Waarom I en Q, als het "gewoon" een frequentie is die varieert?

Een radiochip zoals de AD9361 zendt niet direct "een frequentie die varieert" — hij zendt een RF-signaal uit dat wordt opgebouwd uit twee basisbandsignalen, **I** (in-fase) en **Q** (kwadratuur), die intern in de chip gecombineerd worden met een lokale oscillator om er een radiofrequent signaal van te maken. Dit **IQ-modulatieprincipe** is de standaardmanier waarop moderne radiochips werken, en is flexibeler dan een chip die alleen amplitude of alleen frequentie kan moduleren: met de juiste I- en Q-waarden kun je AM, FM, fasemodulatie en digitale modulatievormen allemaal met dezelfde hardware maken.

Om een FM-signaal via I/Q te maken, geldt wiskundig: als φ(t) de **fase** van de draaggolf is (die continu verandert naargelang de gewenste frequentiedeviatie), dan is:

```
I(t) = cos(φ(t))
Q(t) = sin(φ(t))
```

Dus: in plaats van rechtstreeks een frequentie te moduleren, houd je een **fase** bij die steeds verder oploopt, met een snelheid die op elk moment afhangt van je MPX-audiosignaal — en reken je daar vervolgens de bijbehorende cosinus/sinus van uit. Dat is precies wat dit project in de FPGA doet.

## Hoe dit project dat digitaal opbouwt

```
Audio (I2S, L/R)
      │
      ▼
Upsampler + FIR_Filter        (voorbereiding, ruisonderdrukking)
      │
      ▼
PHASEACCUMULATOR              ← DIT is de kern van de FM-modulatie
      │  (houdt een oplopende fasewaarde bij; elke audio-sample
      │   bepaalt hoe snel de fase op dat moment oploopt =
      │   de ogenblikkelijke frequentiedeviatie)
      ▼
LUT90 (quarter-wave lookup)   ← rekent de fasewaarde om naar I en Q
      │  (een opzoektabel die voor elke fasewaarde het bijbehorende
      │   cos(fase) en sin(fase) teruggeeft — dat is I en Q)
      ▼
IQ-correctie (gain/fase/DC)   (compenseert onvolkomenheden, zie
      │                        de FPGA-implementatie-documentatie)
      ▼
Interpolatie (384→768→...kHz) (onderdrukt spectrale spiegelbeelden,
      │                        zie de interpolatie-documentatie)
      ▼
dac_data_i0 / dac_data_q0     (rechtstreeks de DAC-ingangen van de
                                AD9361 — geen DMA, geen software)
```

**`PHASEACCUMULATOR` is dus niet zomaar een rekenkundig hulpblokje — het ís de FM-modulator.** Het accumuleert bij elke klokcyclus een stukje fase, waarbij de grootte van dat stukje wordt bepaald door de audiowaarde (`sample`) vermenigvuldigd met een schaalfactor (`K_FM`). Een luider of sneller wisselend MPX-signaal laat de fase sneller oplopen, wat neerkomt op een grotere ogenblikkelijke frequentiedeviatie — exact de definitie van FM.

**`LUT90` is de digitale versie van "reken cos(fase) en sin(fase) uit".** In plaats van deze goniometrische functies elke keer opnieuw te berekenen (te traag/te duur in hardware), staat er een kant-en-klare tabel met voorberekende waarden klaar, die op basis van de huidige fasewaarde meteen het juiste I- en Q-paar teruggeeft.

## Waarom rechtstreeks naar de DAC, in plaats van via software/DMA?

De AD9361 kan zijn I/Q-databronnen op twee manieren krijgen:
- **De normale weg**: software (bijvoorbeeld GNU Radio) berekent I/Q-samples en stuurt ze via DMA naar de chip. Handig voor algemene toepassingen, maar niet geschikt om een continu, real-time gemoduleerd FM-signaal te genereren zonder dat de software zelf een volledige, tijdkritische FM-modulator moet zijn.
- **De fabric-directe weg** (wat dit project gebruikt): de FPGA-fabric zelf berekent I en Q, elke keer opnieuw, in hardware, en schrijft die waarden rechtstreeks naar de DAC-ingangen van de AD9361 — zonder ooit via de processor of software te gaan. Dit is sneller, betrouwbaarder qua timing, en precies hoe een "harde" FM-zender hoort te werken: een continu stromende hardwareketen, geen software die per ongeluk kan haperen.

Dit is de reden dat een groot deel van de technische documentatie in dit project gaat over het **blootleggen** van die directe DAC-ingangen in het Vivado-blockdesign (`dac_data_i0_fab`/`dac_data_q0_fab`), het loskoppelen van de oorspronkelijke testtoon-generator die daar al op aangesloten zat, en het correct laten samenwerken van twee verschillende kloksnelheden (de audioketen versus de veel snellere DAC-klok van de AD9361).

## Waarom de extra stappen (interpolatie, IQ-correctie)?

Een direct, digitaal gegenereerd I/Q-signaal is in theorie perfect, maar in de praktijk brengt de hardware twee soorten onvolkomenheden met zich mee:

1. **Spectrale spiegelbeelden**, doordat de audioketen (384 kHz) veel langzamer bijwerkt dan de DAC zelf (~30,72 MHz) — opgelost met een cascade van digitale interpolatiefilters die de update-snelheid stapsgewijs optrekken, zodat de ongewenste spiegelbeelden steeds verder van het gewenste signaal af komen te liggen (zie de interpolatie-documentatie).
2. **IQ-onbalans** — kleine fouten in amplitude, fase of DC-niveau tussen het I- en Q-kanaal, die een storend spiegelbeeld vlak rond de eigen draaggolf kunnen veroorzaken. Dit wordt aangepakt met (a) de ingebouwde kalibratie van de AD9361 zelf (voor fouten in de chip's eigen analoge pad) en (b) een zelfgebouwde correctieketen in de FPGA (gain/fase/DC-offset, instelbaar via software) voor fouten die al in de eigen digitale `LUT90`/`PHASEACCUMULATOR`-keten ontstaan (zie de FPGA-implementatie-documentatie).

## Samengevat: het hele project in één zin

Een FPGA rekent, volledig zelfstandig en in real-time, een MPX-stereosignaal om naar de I- en Q-basisbandwaarden die nodig zijn om dat signaal als FM uit te zenden, en schrijft die waarden rechtstreeks naar de interne AD9361-radiochip van de PlutoSDR — zodat er, zonder tussenkomst van software of een externe modulator, een compleet, uitzendbaar FM-stereosignaal (met piloottoon en RDS) op de RF-uitgang verschijnt.

---

*Zie de overige documenten in deze reeks voor de technische details van elke stap: de integratie in het Pluto-project, de fabric-directe DAC-koppeling, de interpolatiecascade tegen spiegelbeelden, en de IQ-correctie met bijbehorende GUI.*

*Samengevat vanuit een troubleshooting-sessie met Claude (Anthropic).*
