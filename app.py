from flask import Flask, render_template, request, session, redirect, url_for, jsonify, abort
from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os

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

# --- Middleware de sécurité ---
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

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
            return redirect(url_for('hub'))
        
        return render_template('login.html', erreur="Identifiants incorrects.")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
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
    all_movies = list(movies.find({}))
    return render_template('flix_index.html', movies=all_movies)

@app.route('/flix/watch/<movie_id>')
@login_required
def watch(movie_id):
    try:
        movie = movies.find_one({"_id": ObjectId(movie_id)})
        if not movie: abort(404)
        return render_template('watch.html', movie=movie)
    except: abort(400)

# --- Routes ITHChat ---
@app.route('/chat')
@login_required
def forum():
    msgs = list(chats.find({}).sort("_id", -1))
    return render_template('forum.html', user=session['user'], messages=msgs)

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

@app.route('/api/messages')
def get_messages():
    msgs = list(chats.find({}).sort("_id", -1))
    formatted = [{"user": m["user"], "content": m["content"], "date": m["date"], "admin": m.get("admin", False)} for m in msgs]
    return jsonify(formatted)

if __name__ == '__main__':
    app.run(debug=True)
