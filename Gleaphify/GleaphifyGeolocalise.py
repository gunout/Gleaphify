from flask import Flask, request, redirect, jsonify
import sqlite3
import requests  # Pour faire des requêtes HTTP

app = Flask(__name__)

# Base de données pour stocker les liens et les clics
def init_db():
    conn = sqlite3.connect('links.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS links
                 (id INTEGER PRIMARY KEY, original_url TEXT, short_code TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clicks
                 (id INTEGER PRIMARY KEY, link_id INTEGER, ip TEXT, user_agent TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

# Générer un code court pour un lien
def generate_short_code():
    import uuid
    return str(uuid.uuid4())[:8]

# Enregistrer un nouveau lien
@app.route('/shorten', methods=['POST'])
def shorten_url():
    original_url = request.form.get('url')
    if not original_url:
        return "URL manquante", 400

    short_code = generate_short_code()
    conn = sqlite3.connect('links.db')
    c = conn.cursor()
    c.execute("INSERT INTO links (original_url, short_code) VALUES (?, ?)", (original_url, short_code))
    conn.commit()
    conn.close()

    return f"Lien raccourci : http://localhost:5000/{short_code}"

# Rediriger et enregistrer les clics
@app.route('/<short_code>')
def redirect_url(short_code):
    conn = sqlite3.connect('links.db')
    c = conn.cursor()
    c.execute("SELECT original_url FROM links WHERE short_code = ?", (short_code,))
    result = c.fetchone()
    if not result:
        return "Lien non trouvé", 404

    original_url = result[0]

    # Enregistrer les informations du clic (avec consentement)
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent')
    c.execute("INSERT INTO clicks (link_id, ip, user_agent, timestamp) VALUES ((SELECT id FROM links WHERE short_code = ?), ?, ?, datetime('now'))", (short_code, ip, user_agent))
    conn.commit()
    conn.close()

    return redirect(original_url)

# Géolocaliser une adresse IP
def geolocate_ip(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json")
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Impossible de géolocaliser l'IP"}
    except Exception as e:
        return {"error": str(e)}

# Afficher les adresses IP et leurs informations de géolocalisation
@app.route('/ips/<short_code>')
def show_ips(short_code):
    conn = sqlite3.connect('links.db')
    c = conn.cursor()
    c.execute("SELECT ip, user_agent, timestamp FROM clicks WHERE link_id = (SELECT id FROM links WHERE short_code = ?)", (short_code,))
    results = c.fetchall()
    conn.close()

    if not results:
        return jsonify({"error": f"Aucun clic enregistré pour {short_code}"}), 404

    # Ajouter la géolocalisation pour chaque IP
    ip_list = []
    for result in results:
        ip_info = geolocate_ip(result[0])
        ip_list.append({
            "ip": result[0],
            "user_agent": result[1],
            "timestamp": result[2],
            "geolocation": ip_info
        })

    return jsonify(ip_list)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
