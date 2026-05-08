import time
import sys
import select
import requests
import json
from datetime import datetime
from grove.display.jhd1802 import JHD1802
from grove.grove_temperature_humidity_sensor import DHT
from grove.gpio import GPIO 

#ASETUKSET:

AZURE_URL = 'https://websovellus-ffdmaeemhffge9d4.swedencentral-01.azurewebsites.net/lisaa_tieto'

#Määritetään laitteet
sensor = DHT('11', 5)
lcd = JHD1802()
buzzer = GPIO(16, GPIO.OUT)
lcd.clear()


session = requests.Session()

# Muuttujat
paivitys_vali = 0.25
viimeisin_paivitys = 0
viimeisin_lahetys = 0
lahetys_vali = 16.0 
tila = "LAMPOTILA" 
ajastin_alku = 0
kesto_sekuntia = 0 
pakota_lahetys = False

print("Ohjelma käynnistetty majesteettisesti.")
print("Komennot: s10, m5, t1 (ajastin) | r (vain lämpötila)")

try:
    while True:
        nykyhetki = time.time()
        
        # Alustetaan muuttujat
        minuutit = 0
        sekunnit = 0
        ajastin_teksti = "OFF"
        
        # 1. Näppäimistön luku
        if select.select([sys.stdin], [], [], 0)[0]:
            syote = sys.stdin.readline().strip().lower()
            if syote.startswith(('s', 'm', 't')):
                try:
                    tyyppi = syote[0]
                    arvo_str = syote[1:]
                    luku = float(arvo_str) if arvo_str else 1.0
                    if tyyppi == 's': kesto_sekuntia = int(luku)
                    elif tyyppi == 'm': kesto_sekuntia = int(luku * 60)
                    elif tyyppi == 't': kesto_sekuntia = int(luku * 3600)
                    
                    tila = "AJASTIN"
                    ajastin_alku = nykyhetki
                    lcd.clear()
                    pakota_lahetys = True 
                except ValueError: print("Virheellinen syote!")
            elif syote == 'r':
                tila = "LAMPOTILA"
                lcd.clear()
                pakota_lahetys = True

        # Luetaan anturi
        temp, hum = sensor.read()

        # Lasketaan ajastimen tila
        if tila == "AJASTIN":
            jaljella_yhteensa = max(0, int(kesto_sekuntia - (nykyhetki - ajastin_alku)))
            minuutit = jaljella_yhteensa // 60
            sekunnit = jaljella_yhteensa % 60
            ajastin_teksti = f"{minuutit:02d}:{sekunnit:02d}"
            
            if jaljella_yhteensa <= 0:
                tila = "VALMIS"
                ajastin_teksti = "VALMIS"
                lcd.clear()
                pakota_lahetys = True
                for _ in range(3): 
                    buzzer.write(1); time.sleep(0.1); buzzer.write(0); time.sleep(0.1)
        elif tila == "VALMIS":
            ajastin_teksti = "VALMIS"

        # 2. Lähetetään Azuree
        aika_tullut = (nykyhetki - viimeisin_lahetys >= lahetys_vali)
        
        if (aika_tullut or pakota_lahetys) and temp is not None:
            try:
                nyt = datetime.now().isoformat(timespec='seconds')
                
                # Luodaan JSON, jota index.html ja app.py odottavat:
                lahetys_data = {
                    'aika': nyt,
                    'temp': round(temp, 1),
                    'hum': round(hum, 1),
                    'tila': tila,
                    'ajastin': ajastin_teksti
                }
                

                res = session.post(
                    AZURE_URL, 
                    json=lahetys_data, 
                    timeout=15
                )
                
                if res.status_code == 200:
                    print(f"[{nyt}] Azure OK: {temp}C, {hum}%, Ajastin: {ajastin_teksti}")
                else:
                    print(f"Azure virhe: {res.status_code}")
                
                viimeisin_lahetys = nykyhetki
                pakota_lahetys = False
            except Exception as e:
                print(f"Yhteys pätkäisi, yritetään hetken päästä uudelleen... ({e})")

                viimeisin_lahetys = nykyhetki - (lahetys_vali - 2)

        # 3. Lcd näytön päivitys
        if nykyhetki - viimeisin_paivitys >= paivitys_vali:
            if tila == "AJASTIN":
                sykli = (nykyhetki - ajastin_alku) % 10
                if sykli < 5:
                    lcd.setCursor(0, 0); lcd.write("Ajastin paalla  ")
                    lcd.setCursor(1, 0); lcd.write(f"Aika: {ajastin_teksti}    ")
                else:
                    lcd.setCursor(0, 0); lcd.write(f"Temp: {temp:.1f} C      " if temp else "Anturivirhe     ")
                    lcd.setCursor(1, 0); lcd.write(f"Hum:  {hum:.1f} %      " if hum else "                ")
            
            elif tila == "VALMIS":
                lcd.setCursor(0, 0); lcd.write("Ajastus ohi!     ")
                lcd.setCursor(1, 0); lcd.write("VALMIS!            ")
            
            else: 
                lcd.setCursor(0, 0); lcd.write(f"Temp: {temp:.1f} C      " if temp else "Anturivika      ")
                lcd.setCursor(1, 0); lcd.write(f"Hum:  {hum:.1f} %      " if hum else "                ")
            
            viimeisin_paivitys = nykyhetki

        time.sleep(0.1)

except KeyboardInterrupt:
    buzzer.write(0)
    lcd.clear()
    lcd.write("  Suljetaan...")
    time.sleep(1)
    lcd.clear()
