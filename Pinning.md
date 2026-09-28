 
// Stap 3: DC-offset optellen
wire signed [31:0] I_data = i_gained          + {{16{dc_i[15]}}, dc_i};
wire signed [31:0] Q_data = q_phase_corrected + {{16{dc_q[15]}}, dc_q};
```
 
Deze keten is na synthese gecontroleerd in Vivado's RTL-schematic-weergave (Open Elaborated Design → Schematic), waarbij zichtbaar werd bevestigd dat de vier vermenigvuldigers (`RTL_MULT`), de aftrekker (`RTL_SUB`) en de twee optellers (`RTL_ADD`) precies in de bedoelde volgorde en met de juiste bitbreedtes zijn gesynthetiseerd — een nuttige, onafhankelijke bevestiging naast het lezen van de Verilog-code zelf.
 
**Fixed-point-conventie:** `gain_i`/`gain_q`/`phase` gebruiken Q2.14-fixed-point (16-bit signed, 14 fractionele bits), waarbij 16384 overeenkomt met 1,0. De bit-slice `[45:14]` na elke 32×16-bit vermenigvuldiging haalt het resultaat terug naar de oorspronkelijke 32-bit schaal. `dc_i`/`dc_q` zijn daarentegen directe 16-bit signed waarden, geen fixed-point — vandaar de tekenextensie (`{{16{dc_i[15]}}, dc_i}`) in plaats van een schaalbewerking.
 
### Timing-gevolgen van de nieuwe registers
 
Het toevoegen van deze zes GPIO's (die op `clk_fpga_0`, de 100 MHz Zynq-processorklok, worden beschreven vanuit software) en het gebruiken van hun waarden binnen het `clk_49152`-audioklokdomein introduceerde een nieuwe asynchrone klokkruising, op te lossen met dezelfde aanpak als eerder in het project:
 
```tcl
set_clock_groups -asynchronous -group [get_clocks -include_generated_clocks {clk_out1_clk_wiz_i2s clk_out2_clk_wiz_i2s}] -group [get_clocks clk_fpga_0]
```
 
Daarnaast dook een klein, op zichzelf staand timing-tekort op (71 picoseconden, 2 eindpunten) in een geheel ongerelateerd, al bestaand DMA-pad van het originele ADI-ontwerp (`axi_ad9361_dac_dma` → `tx_upack`) — dit bleek een toeval van herschikte chip-plaatsing door de extra logica, niet een fout in de nieuwe registers zelf, en is opgelost met een gerichte `set_false_path` op precies dat pad.
 
Omdat correctiewaarden zoals gain/fase/DC-offset incidenteel en handmatig worden ingesteld (niet continu, tijdkritisch wisselend), is een asynchrone klok-declaratie hier functioneel verantwoord — met de kanttekening dat een multi-bit waarde die op deze manier van klokdomein wisselt in theorie een incoherente (deels oude, deels nieuwe) overgang zou kunnen ondervinden als de waarde precies op het leesmoment verandert. Voor een waarde die je zet en dan laat staan, is dat risico in de praktijk verwaarloosbaar.
 
---
 
## GUI voor live IQ-afregeling (`pluto_iq_gui.py`)
 
Om niet telkens losse `devmem`/`iio_attr`-commando's te hoeven typen, is een Python/tkinter-programma met schuifregelaars gebouwd dat via SSH verbinding maakt met de Pluto en bij elke sliderbeweging het juiste commando op afstand uitvoert.
 
### Functionaliteit
- **Zes schuifregelaars** voor de eigen FPGA-registers: `tone_offset`, `phase`, `gain_i`, `gain_q`, `dc_i`, `dc_q`, met `-`/`+`-knoppen voor fijnafstelling. Gain toont ook de werkelijke factor (16384 = 1,000), fase toont een geschatte hoek in graden.
- **AD9361-sectie**: TX-gain, `calibscale` I/Q, `calibphase` Q, TX-LO instellen, en knoppen voor de `tx_quad`- en `rf_dc_offs`-kalibratietriggers.
- **Neutraal-knop** (reset naar gain=1.0, rest=0) en een testtoon-aan/uit-knop.
- **Automatisch opslaan/laden**: alle instellingen (IP, gebruiker, wachtwoord, alle sliderwaarden, LO-frequentie) worden een halve seconde na elke wijziging en bij het afsluiten weggeschreven naar `pluto_iq_settings.json` naast het script, en bij de volgende start automatisch weer ingelezen — inclusief een optioneel vinkje "auto-verbinden bij start" dat bij het openen meteen verbindt en alle waarden naar de Pluto stuurt.
- **Robuuste JSON-afhandeling**: waarden buiten het toegestane bereik worden afgekapt, ontbrekende of ongeldige velden vallen terug op standaardwaarden, en een corrupt instellingenbestand wordt bewaard als `.bad` in plaats van stilzwijgend overschreven.
 
### Werking onder de motorkap
- Eén achtergrondthread (`Sender`) stuurt de commando's naar de Pluto via een `paramiko`-SSH-verbinding; snel achter elkaar bewegen van een slider resulteert in slechts de laatste waarde die daadwerkelijk verstuurd wordt (per registernaam wordt alleen de nieuwste opdracht bewaard).
- Een `--dry-run`-modus toont alle commando's die verstuurd zouden worden zonder daadwerkelijk verbinding te maken — nuttig om te testen of de juiste `devmem`/`iio_attr`-aanroepen worden opgebouwd.
- Negatieve 16-bit waarden worden correct omgezet naar two's-complement hexadecimaal voor `devmem` (bijvoorbeeld fase -350 → `0xFEA2`).
 
### Installatie
```bash
# Linux
sudo apt install python3-tk
pip install paramiko
 
# Windows
pip install paramiko   # tkinter zit al bij een standaard Python-installatie
```
 
### Bekend aandachtspunt
Na elke herstart van de Pluto staan de AXI GPIO-registers op 0 — dat betekent `gain_i = gain_q = 0`, waardoor de IQ-correctie alles met nul vermenigvuldigt en er geen signaal meer uitkomt totdat de gain opnieuw wordt ingesteld. De GUI lost dit op door bij het verbinden automatisch alle sliderwaarden (met gain standaard op 16384 = 1,0) naar de Pluto te sturen. Zonder de GUI dient hiervoor `iq_tune.sh reset` te worden gebruikt.
 
---
