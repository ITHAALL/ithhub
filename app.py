from flask import Flask, render_template, request, session, redirect, url_for, jsonify, abort
from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from bson.objectid import ObjectId
import os, requests, time, threading

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "hub_secret_key_123")

# --- Connexion MongoDB ---
client = MongoClient(os.getenv("MONGODB_URI"), server_api=ServerApi('1'))
db_chat = client["ithchat"]
db_flix = client["ithflix"]

# Collections
accounts = db_chat["accounts"]
chats = db_chat["chats"]
movies = db_flix["movies"]

# --- Fonctions

# Authentification
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# Logs Webhook
def send_discord_embed(webhook_url, title, description, color=0x007bff, thumbnail_url=None, footer_text="📁 ITH-Hub Logs"):
    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "thumbnail": {"url": thumbnail_url} if thumbnail_url else {},
            "footer": {"text": footer_text},
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Erreur Webhook : {e}")
        return False

# --- Routes Authentification ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('hub'))
    
    if request.method == 'POST':
        user_input = request.form.get('user')
        pass_input = request.form.get('pass')
        
        user_data = accounts.find_one({"user": user_input})
        if user_data and pass_input == user_data.get("password"):
            session['user'] = user_data.get('user')
            session['is_admin'] = user_data.get('admin', False)
            if session['is_admin'] == True:
                send_discord_embed(os.getenv("WEBHOOK_LOGS"), "🔗 Nouvelle connexion", f"`{user_input}` s'est connecté à son compte ITH-Hub.")
            else:
                send_discord_embed(os.getenv("WEBHOOK_LOGS"), "🔗 Nouvelle connexion", f"`{user_input}` s'est connecté à son compte ITH-Hub sous ||`{request.remote_addr}`||.")
            return redirect(url_for('hub'))
        
        return render_template('login.html', erreur="Identifiants incorrects.")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    send_discord_embed(os.getenv("WEBHOOK_LOGS"), "⛓️‍💥 Nouvelle déconnexion", f"`{session['user']}` s'est déconnecté de son compte ITH-Hub.")
    session.clear()
    return redirect(url_for('login'))

# --- Route Hub ---
@app.route('/hub')
@login_required
def hub():
    return render_template('hub.html', user=session['user'])

# --- Routes ITHFlix ---
@app.route('/flix')
@login_required
def flix_index():
    all_movies = list(movies.find({}).sort("_id", -1))
    return render_template('flix_index.html', movies=all_movies)

@app.route('/flix/watch/<movie_id>')
@login_required
def watch(movie_id):
    try:
        movie = movies.find_one({"_id": ObjectId(movie_id)})
        
        if movie is None:
            print(f"❓ Film introuvable pour l'ID: {movie_id}")
            abort(404)
            
        return render_template('watch.html', movie=movie)
    except Exception as e:
        print(f"❌ Erreur lors du chargement du film: {e}")
        abort(400)

# --- Routes ITHChat ---
@app.route('/chat')
@login_required
def forum():
    #msgs = list(chats.find({}).sort("_id", 1))
    #return render_template('forum.html', user=session['user'], messages=msgs)
    return render_template('chat_unavailable.html')

@app.route('/chat/post', methods=['POST'])
@login_required
def poster():
    contenu = request.form.get('contenu', '').strip()
    if contenu:
        chats.insert_one({
            "user": session['user'],
            "content": contenu,
            "date": datetime.now().strftime("%H:%M"),
            "admin": session.get('is_admin', False)
        })
    return redirect(url_for('forum'))

@app.route('/ping')
def ping():
    return "Pong !"

def ping_self():
    while True:
        try:
            requests.get("https://api-ubf1.onrender.com/ping")
            print("Keep-alive : Ping envoyé avec succès.")
        except Exception as e:
            print(f"Keep-alive : Erreur de ping {e}")
        
        time.sleep(60) 

if __name__ == '__main__':
    threading.Thread(target=ping_self, daemon=True).start()
    app.run(debug=False)
