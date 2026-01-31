from flask import Flask, jsonify, request, render_template_string
from datetime import datetime

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Mon Mini Réseau</title>
    <style>
        body { font-family: sans-serif; max-width: 500px; margin: auto; background: #f0f2f5; }
        .post { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .pseudo { font-weight: bold; color: #1877f2; }
        input, button { width: 100%; padding: 10px; margin-top: 5px; border-radius: 5px; border: 1px solid #ddd; }
        button { background: #1877f2; color: white; cursor: pointer; border: none; }
    </style>
</head>
<body>
    <h2>Mon Flux Social</h2>
    <div style="background: white; padding: 15px; border-radius: 8px;">
        <input type="text" id="pseudo" placeholder="Ton pseudo">
        <input type="text" id="msg" placeholder="Quoi de neuf ?">
        <button onclick="envoyer()">Publier</button>
    </div>
    <div id="flux"></div>

    <script>
        function chargerMessages() {
            fetch('/api/messages')
                .then(res => res.json())
                .then(data => {
                    let html = '';
                    data.forEach(m => {
                        html += `<div class="post"><span class="pseudo">${m.pseudo}</span> <small>${m.date}</small><p>${m.contenu}</p></div>`;
                    });
                    document.getElementById('flux').innerHTML = html;
                });
        }

        function envoyer() {
            const pseudo = document.getElementById('pseudo').value;
            const contenu = document.getElementById('msg').value;
            fetch('/api/poster', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({pseudo, contenu})
            }).then(() => {
                document.getElementById('msg').value = '';
                chargerMessages();
            });
        }
        setInterval(chargerMessages, 3000); // Rafraîchit toutes les 3s
        chargerMessages();
    </script>
</body>
</html>
'''

app = Flask(__name__)

# Notre base de données temporaire (en attendant Postgres)
flux_messages = [
    {"pseudo": "Admin", "contenu": "Bienvenue sur mon nouveau réseau social !", "date": "10:00"}
]

# Route pour afficher la page web (HTML)
@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

# Route API pour récupérer les messages (JSON)
@app.route('/api/messages', methods=['GET'])
def get_messages():
    return jsonify(flux_messages)

# Route API pour poster un nouveau message
@app.route('/api/poster', methods=['POST'])
def poster():
    data = request.json
    nouveau_post = {
        "pseudo": data.get('pseudo', 'Anonyme'),
        "contenu": data.get('contenu', ''),
        "date": datetime.now().strftime("%H:%M")
    }
    flux_messages.insert(0, nouveau_post) # On met le plus récent en haut
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)
