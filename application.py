from flask import Flask

app = Flask(__name__);

app.route("/claim", methods=["GET", "POST"])
def claim():
    pass