from flask import Flask, jsonify

app = Flask(__name__)

# Tes données
livres = [
    {'id': 1, 'titre': 'Le Petit Prince', 'auteur': 'Saint-Exupéry'},
    {'id': 2, 'titre': '1984', 'auteur': 'George Orwell'}
]

@app.route('/')
def home():
    return "Bienvenue sur mon API ! Allez sur /api/livres pour voir les données."

@app.route('/api/livres', methods=['GET'])
def obtenir_livres():
    return jsonify(livres)

# Cette partie ne sera utilisée QUE si tu lances le fichier sur ton PC.
# Sur Render, c'est Gunicorn qui ignorera ce bloc et lancera l'app directement.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
