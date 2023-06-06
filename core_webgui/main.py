# app.py
from flask import Flask, jsonify, render_template
import json

app = Flask(__name__)

@app.route('/config')
def get_config():
    with open('../config.json') as config_file:
        config = json.load(config_file)
    clips = config.get('clips', [])
    transformed_clips = [
        {
            "name": clip["title"],
            "start": clip["begin"],
            "end": clip["end"]
        }
        for clip in clips
    ]
    return jsonify(transformed_clips)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
