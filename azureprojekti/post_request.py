import requests 
import json
from datetime import datetime
import random
import time

lampotila = 5

while True:
    nyt = datetime.now().isoformat(timespec='seconds') 

    lampotila += random.randint(-1, 1) 


    lahetys = {
        'mittaus': {
            nyt: lampotila
        }
    }

    viesti = json.dumps(lahetys)
    print(viesti)

    vastaus = requests.post(
        'http://127.0.0.1:5000/lisaa_tieto',
        data=viesti,
        headers={'Content-Type': 'application/json'}
    )

    print(vastaus.status_code, vastaus.text)

    time.sleep(5) 