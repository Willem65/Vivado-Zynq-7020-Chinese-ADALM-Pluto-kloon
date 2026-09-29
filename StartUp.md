Schrijf eerst de software inhoud van de zip :  SD-card-pluto-wuffum.zip 
naar het SD kaartje.



Installeer python op je computer:   curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py

installeer pip op je computer:      python3 get-pip.py

installeer paramika:                python -m pip install paramiko

Start het PY bestand op

Je krijgt een Gui te zien waarmee je de PLUTO-SDR kunt instellen, Frequentie en IQ afregeling. 





Als je alle lle python over wilt slaan,  dan kun je het ook even aan de gang krijgen via ssh Putty.

met :

devmem 0x41200000 32 10000    # tone_offset (0 = normale audio, >0 = testtoon met deze offset)
devmem 0x41210000 32 0        # phase
devmem 0x41220000 32 16384    # gain_i (16384 = 1.0 in Q2.14)
devmem 0x41230000 32 16384    # gain_q

iio_attr -u ip:192.168.1.148 -c -o ad9361-phy altvoltage1 frequency 1285000000



