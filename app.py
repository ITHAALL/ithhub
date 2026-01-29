from flask import Flask, jsonify, request

app = Flask(__name__)

kick_queue = []

@app.route('/')
def home():
    return "API de Modération Active"

@app.route('/add_kick', methods=['GET'])
def add_kick():
    user_id = request.args.get('user_id')
    if user_id:
        if user_id not in kick_queue:
            kick_queue.append(user_id)
        return f"L'utilisateur {user_id} a été ajouté à la liste de kick."
    return "Erreur : user_id manquant", 400

@app.route('/get_kicks', methods=['GET'])
def get_kicks():
    return jsonify({"kick_list": kick_queue})

@app.route('/admin')
def admin_panel():
    return '''
        <h1>Panel de Modération</h1>
        <input type="text" id="userId" placeholder="Entrez l'ID Roblox">
        <button onclick="kick()">Kicker le joueur</button>
        <script>
            function kick() {
                const id = document.getElementById('userId').value;
                fetch('/add_kick?user_id=' + id)
                    .then(response => response.text())
                    .then(data => alert(data));
            }
        </script>
    '''

@app.route('/clear_kicks', methods=['POST'])
def clear_kicks():
    global kick_queue
    kick_queue = []
    return "Liste vidée"
