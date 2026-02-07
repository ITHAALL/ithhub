from flask import Flask
from threading import Thread

keep_alive_app = Flask('')

@keep_alive_app.route('/ping')
def ping():
    return "Statut : Réveillé !", 200

def run():
    keep_alive_app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
