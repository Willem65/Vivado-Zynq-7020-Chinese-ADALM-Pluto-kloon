Sample-rate bepaald wat de hoogste audio frequentie zal zijn.
Hoogste bruikbare audio frequentie is de sample rate gedeeld door 2 (Shannon Nyquist). 
Stel je hebt een blok golf van 192 KHz dan is de hoogste audio frequentie 96 KHz. 
Maar willen we 16 bits aan waarde ( wat dan de amplitude vertegenwoordigt ) in die tijd stoppen dan wordt dat 16 bitjes voor het lage deel en voor het hoge deel. 
Dus de bitrate moet omhoog.

Is: (16+16)*192KHz is 6.144MHz, de 16 bits vertegenwoorden de waarde van de amplitude van het audio signaal. 

Maar omdat i2s tegenwoordig allemaal 32 bits is, is het (32+32)*192KHz=12.288MHz bit clock nodig.

Dus sample-rate omhoog of aantal bits omhoog betekend een hogere bit clock. 
Nogmaals : sample-rate omhoog (bit klok omhoog)
aantal bits omhoog (bit klok omhoog) en ( de nauwkeurigheid van de amplitude, bepaald ook de hoeveel punten per sample, bij de hoogste frequentie minimaal 2 samples )
en hoeveel kanalen ? ( tegenwoordig 32 bits per hoog lrclk en 32 bits laag lrclk is 64 bits per frame)
En bij een sample-rate van 384KHz wordt de bit clock weer 2 maal zo hoog (32+32)*384KHz is 24.576MHz, dus 32 bits voor het linker kanaal en 32 bits voor het rechter kanaal.
In de praktijk worden er vaak toch maar weer van die 32 bits maar de bovenste 16 bits gebruikt.
En dan is i2s ook nog eens een clockbit delayed geklokt , dan komt door de historie van i2s. 
Dat is historisch gegroeid omdat 32‑bit I²S makkelijker te routen is in hardware.
• 	WS (LRCLK) verandert één bit vóór de MSB
• 	Data wordt gelezen op de rising edge
• 	Data verandert op de falling edge
In de begintijd van digitale audio (Philips) werden schuifregisters gebruikt
De hardware heeft dan precies één BCLK-cyclus de tijd om de interne registers te "latch-en" (vast te zetten) voordat de eerste echte bit van het nieuwe kanaal binnenkomt
Om een sinus van de allerhoogste frequentie (de Nyquist-frequentie) te reproduceren, heb je twee volledige cycli van de LRCLK nodig.
Omdat je 2 punten voor zowel links en rechts nodig hebt, dus 4  momenten in tijd.
In de eerste links-rechts-klok zit achtereenvolgend links en rechts. Die kunnen dus het zelfde positive amplitude punt hebben, en bij de volgende links-rechts-klok het tweede negative punt hebben om achtereenvolgend de sinussen te kunnen reproduceren. ( dit is toch best grappig, eerst 2 positive bulten en daarna 2 negative bulten )
Wat vind je van deze uitleg/redenering over i2s van mij?


PhaseAccumular : 

Dit is eigenlijk de motor die bepaald hoe snel je door de lut tabel gaat, waar de hoeveelheid punten in staan met de bijbehorende amplitude van het signaal, wat ook de vorm van het signaal bepaald , in ons geval sinusvormig.
Het gaspendaal is de stapgrootte.
Het gaspendaal word bediend door de modulatie.
Door deze phase accumulator worden de waardes met een bepaalde snelheid  uit de lut tabel gelezen.
Dus met een fase-accumulator die bijvoorbeeld  32 bits is  en je sample-rate 192 kHz
Bij 192 kHz duurt het dan 2^32 = 4294967296 klokslagen om één rondje te draaien.Dat betekent dat je theoretisch een toon kunt maken van 192.000/4.294.967.296=0,00004 Hz. Dat is één trilling per 7 uur! De laagste frequentie is dus bijna altijd "laag genoeg".
De Tabel bepaalt de: zuiverheid van de sinus vorming
stel je jezelf de vraag: "Hoeveel trapjes mag mijn sinus hebben?"
•	In het geval van weinig punten (bijv. 2 of 4): Als je heel langzaam door de tabel gaat, blijft de uitgang heel lang op "hoog" staan en dan heel lang op "laag". Je krijgt een blokgolf. Een blokgolf zit vol met harmonischen (bijgeluiden) die je niet wilt in een zuivere sinus.
•	Veel punten 16.384 x 4 ( 4 kwadranten ) wat ik nu gebruik. Als je heel langzaam gaat ( lage tonen ), verandert de waarde bij bijna elke stap van de accumulator een heel klein beetje. De trapjes zijn zo klein dat ze na het filter van de DAC onzichtbaar zijn.
Bij het ontwerpen van je LUT (Look-Up Table) kijk je vooral naar de Signal-to-Noise Ratio (SNR) en de Total Harmonic Distortion (THD):
1.	Bit-diepte (16-bit): Dit bepaalt de verticale nauwkeurigheid. 16-bit geeft een theoretische dynamiek van ongeveer 96 dB. Dat is CD-kwaliteit en erg goed.
2.	Aantal adressen (16.384 kwart-sinus): Dit bepaalt de horizontale nauwkeurigheid. Hoe meer punten, hoe minder "fase-ruis" je hebt. Met 16k punten heb je een extreem schone sinus.
De vuistregel
Als je een tabel ontwerpt, wil je dat de fout die ontstaat door de "trapjes" (zowel horizontaal als verticaal) kleiner is dan wat de rest van je systeem kan weergeven.
•	Voor 16-bit audio: Is een tabel van 1024 of 2048 punten vaak al genoeg om een "schone" sinus te horen.
•	Jouw 16.384 punten: Dat is "overkill" op een goede manier. Je hebt hiermee een laboratorium-waardige precisie. Zelfs als je heel diep inzoomt op je laagste frequentie, zal het een prachtige, vloeiende lijn blijven.
Samengevat: Je hoeft dus niet bang te zijn dat je de laagste frequentie niet haalt, maar door je grote tabel heb je ervoor gezorgd dat die lage frequentie ook echt als een sinus klinkt, en niet als een blokgolf.
De uitgangs frequentie:
fout = M ⋅ fclk / 2^32
Waarbij:
•	fout = de gewenste audiofrequentie.
•	M = de Phase Increment (jouw stapgrootte).
•	fclk = de sample-rate (bijv. 192 kHz).
•	2N = de maximale waarde van je accumulator (bijv. 2^32 voor een 32-bit teller).
