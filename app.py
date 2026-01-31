from flask import Flask, render_template, request, session, redirect, url_for
from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os, string, random

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"), server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("✅ La connexion avec MongoDB a été établie avec succès !")
except Exception as e:
    print(f"❌ Erreur obtenue en essayant de se connecter avec MongoDB : {e}")

ithchat_cluster = client["ithchat"]
accounts_collection = ithchat_cluster["accounts"]
chats_collection = ithchat_cluster["chats"]

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "une_cle_par_defaut_tres_longue")

def generate_id(size=10, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
    return ''.join(random.choice(chars) for _ in range(size))

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form.get('user')
        pass_input = request.form.get('pass')
        
        data = list(accounts_collection.find({"user": user_input}))
        if len(data) != 0:
            if pass_input == data[0].get("password", ""):
                # Mot de passe correct
                session['user'] = data[0].get('user', 'Invité')
                session['is_admin'] = data[0].get('admin', False)
                return redirect(url_for('forum'))
            else:
                # Mot de passe incorrect
                return render_template('login.html', erreur="Le mot de passe est incorect, fais un effort frérot...")
        else:
            # User introuvable
            return render_template('login.html', erreur="Ce compte n'existe pas gros malin")
    
    return render_template('login.html')

@app.route('/poster', methods=['POST'])
def poster():
    if 'user' in session:
        nouveau_post = {
            "_id": generate_id(),
            "user": session['user'],
            "content": request.form.get('contenu'),
            "date": datetime.now().strftime("%H:%M"),
            "admin": session.get('is_admin', False)
        }
        chats_collection.insert_one(nouveau_post)

    return redirect(url_for('forum'))

@app.route('/forum')
def forum():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    return render_template('forum.html', user=session['user'], messages=list(chats_collection.find({}).sort("date", -1)))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/reset_chat')
def reset_chat():
    if session.get('is_admin') == True:
        chats_collection.delete_many({})
        print("💥 Le chat a été réinitialisé par un admin.")
    
    return redirect(url_for('forum'))

if __name__ == '__main__':
    app.run(debug=True)