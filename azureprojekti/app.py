from flask import Flask, request, render_template, jsonify
import sqlite3
import os

app = Flask(__name__)


basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "mittaukset.db3")


viimeisin_ajastin_tieto = "OFF"

def alusta_tietokanta():
    """Luo tietokannan ja taulun kaynnistyksessa, jos niita ei ole."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mittaukset (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aika TEXT,
                    lampotila REAL,
                    kosteus REAL
                )
            """)
        print("Tietokanta alustettu.")
    except Exception as e:
        print(f"Tietokantavirhe alustuksessa: {e}")


alusta_tietokanta()

@app.route('/', methods=['GET'])
def index():
    """Paasivu: hakee mittaushistorian."""
    try:
        with sqlite3.connect(db_path) as conn:

            tiedot = conn.execute(
                "SELECT aika, lampotila, kosteus FROM mittaukset ORDER BY id DESC LIMIT 20"
            ).fetchall()
        

        return render_template('index.html', taulukko=list(reversed(tiedot)))
    except Exception as e:
        return f"Palvelinvirhe: {e}", 500

@app.route('/lisaa_tieto', methods=['POST'])
def lisaa_tieto():
    """Vastaanottaa datan Raspberry Pi:lta."""
    global viimeisin_ajastin_tieto
    try:
        data = request.get_json(force=True)
        

        viimeisin_ajastin_tieto = data.get('ajastin', 'OFF')
        
        aika = data.get('aika')
        temp = data.get('temp')
        hum = data.get('hum')


        with sqlite3.connect(db_path, timeout=10) as conn:
            conn.execute(
                "INSERT INTO mittaukset (aika, lampotila, kosteus) VALUES (?, ?, ?)",
                (aika, temp, hum)
            )
        return "ok", 200
    except Exception as e:
        print(f"Virhe vastaanotossa: {e}")
        return str(e), 400

@app.route('/paivita', methods=['GET'])
def paivita():
    """Selain kutsuu tata 5 sekunnin valein paivittaakseen UI:n."""
    global viimeisin_ajastin_tieto
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT aika, lampotila, kosteus FROM mittaukset ORDER BY id DESC LIMIT 1"
            ).fetchone()
        
        if row:
            return jsonify({
                'aika': row[0],
                'temp': row[1],
                'hum': row[2],
                'ajastin': viimeisin_ajastin_tieto # Lahetetaan ajastin selaimelle
            })
        return jsonify({'ajastin': viimeisin_ajastin_tieto})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)