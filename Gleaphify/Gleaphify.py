from flask import Flask, request, redirect
import sqlite3

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

# Afficher les statistiques des clics
@app.route('/stats/<short_code>')
def show_stats(short_code):
    conn = sqlite3.connect('links.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM clicks WHERE link_id = (SELECT id FROM links WHERE short_code = ?)", (short_code,))
    click_count = c.fetchone()[0]
    conn.close()

    return f"Nombre de clics pour {short_code} : {click_count}"

# Afficher les adresses IP des utilisateurs qui ont cliqué sur un lien court
@app.route('/ips/<short_code>')
def show_ips(short_code):
    conn = sqlite3.connect('links.db')
    c = conn.cursor()
    c.execute("SELECT ip, user_agent, timestamp FROM clicks WHERE link_id = (SELECT id FROM links WHERE short_code = ?)", (short_code,))
    results = c.fetchall()
    conn.close()

    if not results:
        return f"Aucun clic enregistré pour {short_code}", 404

    # Formater les résultats pour l'affichage
    ip_list = []
    for result in results:
        ip_list.append({
            "ip": result[0],
            "user_agent": result[1],
            "timestamp": result[2]
        })

    return ip_list

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
