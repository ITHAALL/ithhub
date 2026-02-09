from flask import Flask, render_template, request, session, redirect, url_for, abort, send_file
from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from bson.objectid import ObjectId
import os, requests, time, math, io, re
from collections import Counter

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
def get_dms(token):
    headers = {"Authorization": token, "Content-Type": "application/json"}
    response = requests.get(f"https://discord.com/api/v9/users/@me/channels", headers=headers)
    dms_list = []
    
    if response.status_code == 200:
        for info in response.json():
            if info.get('recipients'):
                user = info['recipients'][0]
                uid = user.get('id')
                av = user.get('avatar')
                avatar_url = f"https://cdn.discordapp.com/avatars/{uid}/{av}.png?size=64" if av else "https://cdn.discordapp.com/embed/avatars/0.png"
                
                dms_list.append({
                    "channel_id": info.get('id'),
                    "user_id": uid,
                    "username": user.get('username'),
                    "avatar": avatar_url
                })
    return dms_list

def check_token(token : str) -> bool:
    try:
        headers = {"Authorization": token, "Content-Type": "application/json"}
        token_check = requests.get("https://discordapp.com/api/v9/users/@me", headers=headers)
        if token_check.status_code != 200:
            raise Exception()
    except Exception as e:
        return False
    else:
        return True
    
def check_channel(token, channel_id):
    try:
        headers = {"Authorization": token, "Content-Type": "application/json"}
        params = {"limit": 1}
        response = requests.get(f"https://discord.com/api/v9/channels/{channel_id}/messages", headers=headers, params=params)
        if response.status_code != 200:
            raise Exception
    except Exception:
        return False
    else:
        return True

def save_dm(token, channel_id, message_count = 50):
    # === VERIFICATION DU TOKEN ===
    if check_token(token) != True:
        print("Token invalide")
        return
    
    # === VERIFICATION DU CHANNEL ===
    if check_channel(token, channel_id) != True:
        print("Token invalide")
        return
    
    headers = {"Authorization": token, "Content-Type": "application/json"}
    print("📥 Récupération des messages...")
    requests_count = math.ceil(message_count / 50)
    last_message_id = None
    messages = []
    users = {}

    for _ in range(requests_count):
        params = {"limit": 50}
        if last_message_id:
            params["before"] = last_message_id

        response = requests.get(f"https://discord.com/api/v9/channels/{channel_id}/messages", headers=headers, params=params)
        while response.status_code == 429:
            time.sleep(response.json().get("retry_after", 5))
            response = requests.get(f"https://discord.com/api/v9/channels/{channel_id}/messages", headers=headers, params=params)

        if response.status_code != 200:
            break

        batch = response.json()
        if not batch:
            break

        for msg in batch:
            users[msg["author"]["id"]] = msg["author"]

        last_message_id = batch[-1]["id"]
        messages.extend(batch)
        if len(messages) >= message_count:
            break

    print(f"✅ {len(messages)} messages récupérés.")

    # === CONSTRUCTION DU TXT  ===
    lines = []
    
    for msg in reversed(messages):
        date_obj = datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00"))
        date_str = f"{date_obj.day}/{date_obj.month} à {date_obj.strftime('%H:%M')}"        

        username = msg["author"]["username"]
        content = msg.get("content") or "[Fichier ou Message Vide]"
        
        content = content.replace("\n", " ")

        line = f"[{username}] ({date_str}) : {content}"
        lines.append(line)

        for att in msg.get("attachments", []):
            lines.append(f"     -> Pièce jointe : {att['url']}")

    # === GÉNÉRATION DU FICHIER .TXT ===
    filename = f"backup_{channel_id}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"✅ Backup texte terminée : {filename}")


def get_stats(token, cid):
    headers = {'Authorization': token}
    all_messages = []
    last_id = None
    
    for _ in range(10):
        url = f'https://discord.com/api/v9/channels/{cid}/messages?limit=100'
        if last_id: url += f'&before={last_id}'
        res = requests.get(url, headers=headers)
        if res.status_code != 200: break
        batch = res.json()
        if not batch: break
        all_messages.extend(batch)
        last_id = batch[-1]['id']

    if not all_messages: return {"error": "Vide"}

    users = {}
    stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'et', 'est', 'que', 'qui', 'dans', 'pour', 'pas', 'ce', 'sur', 'ca', 'on', 'je', 'tu', 'de'}

    sorted_msgs = sorted(all_messages, key=lambda x: x['timestamp'])
    last_msg = None

    for msg in sorted_msgs:
        uid = msg['author']['id']
        content = msg.get('content', '')
        
        if uid not in users:
            users[uid] = {
                "name": msg['author']['username'],
                "msg_count": 0, "attachments": 0, "chars": 0,
                "words_list": [], "emojis_list": [], "hours": [],
                "response_times": [], "insults_count": 0, "questions": 0
            }
        
        u = users[uid]
        u["msg_count"] += 1
        u["attachments"] += len(msg.get('attachments', []))
        u["chars"] += len(content)
        
        ts = datetime.fromisoformat(msg['timestamp'].replace("+00:00", ""))
        u["hours"].append(ts.hour)

        if content:
            if "?" in content: u["questions"] += 1
            
            emojis = re.findall(r'<a?:\w+:\d+>|[\u263a-\U0001f645]', content)
            u["emojis_list"].extend(emojis)

            words = re.findall(r'\w{3,}', content.lower())
            u["words_list"].extend([w for w in words if w not in stop_words])

    final_stats = []
    for uid, d in users.items():
        top_words = [f"{w} ({c})" for w, c in Counter(d["words_list"]).most_common(3)]
        top_emoji = Counter(d["emojis_list"]).most_common(1)
        
        most_active_hour = Counter(d["hours"]).most_common(1)[0][0] if d["hours"] else 0
        
        final_stats.append({
            "name": d["name"],
            "msg_count": d["msg_count"],
            "top_words": top_words,
            "best_emoji": top_emoji[0][0] if top_emoji else "Aucun",
            "activity": f"{most_active_hour}h",
            "questions": d["questions"],
            "avg_len": round(d["chars"] / d["msg_count"], 1),
            "vibe": "Grand Bavard" if d["chars"] / d["msg_count"] > 50 else "Rapide & Efficace"
        })

    return {"users": final_stats}

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

@app.route('/watch/<movie_id>')
def watch(movie_id):
    movie = movies.find_one({"_id": ObjectId(movie_id)})
    
    if not movie:
        return "Film non trouvé", 404

    video_url = movie.get('source')
    
    return render_template('watch.html', movie=movie, video_url=video_url)

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

# --- Routes ITHSave ---
@app.route('/save')
@login_required
def save_home():
    return render_template('save_index.html')

@app.route('/save/list', methods=['POST'])
@login_required
def save_list():
    token = request.form.get('token')
    print(f'test {token}')
    if check_token(token):
        session['ds_token'] = token
        dms = get_dms(token)
        return render_template('save_index.html', dms=dms)
    return render_template('save_index.html', error="Token Discord invalide.")
    
@app.route('/save/run/<channel_id>', methods=['POST'])
@login_required
def save_run(channel_id):
    token = session.get('ds_token')
    if not token: 
        return "Session expirée", 403
    
    filename = f"backup_{channel_id}.txt"
    
    try:
        save_dm(token, channel_id, message_count=1000)
        
        if not os.path.exists(filename):
            return "Erreur : Fichier non généré", 500

        return_data = io.BytesIO()
        with open(filename, 'rb') as f:
            return_data.write(f.read())
        return_data.seek(0)

        os.remove(filename)
        print(f"🗑️ Fichier {filename} supprimé avec succès.")

        return send_file(
            return_data,
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        if os.path.exists(filename):
            os.remove(filename)
        return f"Erreur : {str(e)}", 500
    
# --- Routes ITHStats ---
@app.route('/stats')
@login_required
def stats_home():
    # On réutilise le token de ITHSave s'il existe
    token = session.get('ds_token')
    if not token:
        # Si pas de token, on redirige vers la page où on entre le token
        return redirect(url_for('save_home')) 

    dms = get_dms(token)
    return render_template('stats_selection.html', dms=dms)

@app.route('/stats/view/<cid>')
@login_required
def stats_page(cid):
    token = session.get('ds_token')
    if not token: 
        return redirect(url_for('save_home'))
    
    # Appel de la fonction de calcul
    data = get_stats(token, cid) 
    
    if "error" in data:
        return render_template('save_index.html', error="Impossible d'analyser ce salon.")
        
    return render_template('stats.html', stats=data)

if __name__ == '__main__':
    app.run(debug=False)
