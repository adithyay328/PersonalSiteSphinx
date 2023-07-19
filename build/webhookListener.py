"""
This is a flask server that deals
with github webhook messages
"""
import json

from flask import Flask, request

app = Flask(__name__)

LOG_FILE = "logs.txt"

@app.route('/payload', methods=['POST'])
def handleMessage():
    """
    Handles a webhook message from github
    """
    with open(LOG_FILE, "a") as f:
        f.write(str(request.get_json()) + "\n")

    return "OK"