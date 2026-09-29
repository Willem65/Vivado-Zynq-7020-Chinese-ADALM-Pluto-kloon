# Pluto-SDR IQ-afregeling en Installatie

Deze handleiding beschrijft hoe je de software voor de Pluto-SDR instelt en gebruikt via een Python-GUI of handmatig via SSH.

Voorbereiding van de SD-kaart
Schrijf eerst de software-inhoud van het zip-bestand `SD-card-pluto-wuffum.zip` naar het SD-kaartje.
Stop dan het kaartje in de pluto sdr.

---

## 1. Methode A: Python GUI (Aanbevolen)

Volg onderstaande stappen om de grafische interface te installeren en te starten:

1. **Installeer Python en pip** op je computer:
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

Je krijgt nu een GUI te zien waarmee je de PLUTO-SDR kunt instellen, inclusief de frequentie en de IQ-afregeling.

---

## 2. Methode B: Alternatief via SSH (PuTTY)

Wil je alle Python-stappen liever overslaan? Dan kun je de instellingen ook direct handmatig configureren via SSH (bijvoorbeeld met PuTTY):

```bash
devmem 0x41200000 32 10000    # tone_offset (0 = normale audio, >0 = testtoon met deze offset)
devmem 0x41210000 32 0        # phase
devmem 0x41220000 32 16384    # gain_i (16384 = 1.0 in Q2.14)
devmem 0x41230000 32 16384    # gain_q

iio_attr -u ip:192.168.1.148 -c -o ad9361-phy altvoltage1 frequency 1285000000


