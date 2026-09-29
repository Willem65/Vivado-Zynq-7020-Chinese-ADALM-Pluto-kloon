Schrijf eerst de software inhoud van de zip :  SD-card-pluto-wuffum.zip 
naar het SD kaartje.



Installeer python op je computer

installeer pip op je computer

installeer paramika met python pip

Start het PY bestand op

Je krijgt een Gui te zien waarmee je de PLUTO-SDR kunt instellen, Frequentie en IQ afregeling. 



Als je alleen even alle python over wilt slaan dan kun je het ook even aan de gang krijgen via ssh Putty.

met :

devmem 0x41200000 32 10000    # tone_offset (0 = normale audio, >0 = testtoon met deze offset)
devmem 0x41210000 32 0        # phase
devmem 0x41220000 32 16384    # gain_i (16384 = 1.0 in Q2.14)
devmem 0x41230000 32 16384    # gain_q



