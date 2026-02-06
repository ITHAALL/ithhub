from flask import Flask, render_template, abort
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"), server_api=ServerApi('1'))
ithflix_cluster = client["ithflix"]
movies_collection = ithflix_cluster["movies"]

app = Flask(__name__)

@app.route('/')
def index():
    movies = list(movies_collection.find({}))
    return render_template('index.html', movies=movies)

@app.route('/watch/<movie_id>')
def watch(movie_id):
    try:
        movie = movies_collection.find_one({"_id": ObjectId(movie_id)})
        
        if movie is None:
            abort(404)
            
        return render_template('watch.html', movie=movie)
    except Exception:
        abort(400)

if __name__ == '__main__':
    app.run(debug=True)
