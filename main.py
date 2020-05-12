from flask import Flask, request, render_template, redirect
import flask
from qrgen import GPQRGen
from airtable import Airtable
import json
import requests

#Getting config stuff
with open("config.json") as f:
    config = json.load(f);
    airtable_auth_key = config["airtable_auth_key"]
    base_key = config["base_key"] 
    client_id = config["client_id"]
    clientSecret = config["client_secret"]
    secretKey = config["secret_key"]

app = Flask(__name__)
app.secret_key = secretKey

#Airtable bases
claims_base = Airtable(base_key, "Coin Claims", api_key=airtable_auth_key)
admin_base = Airtable(base_key, "Verified Generators", api_key=airtable_auth_key)

@app.route("/", methods=["GET", "POST"])
def index():
    return ("This is the index.", 200)

@app.route("/generate", methods=["GET", "POST"])
def generate():
    #Making sure that admin has logged in before
    try:
        admin_record = admin_base.search("Slack Tag", flask.session["authdict"]["name"])
        logged_in = admin_record[0]["fields"]["Logged In?"]
        username = admin_record[0]["fields"]["Slack Tag"]
    except KeyError:
        logged_in = False
        
    if request.method == 'POST':
        amount = request.form.get("amount")
        flask.session["amount"] = int(amount)
        return redirect("/qrcode")
    
    if not logged_in:
        return render_template("adminlogin.html", clientId=client_id)
    else:
        return render_template("generate.html", name=username)
    
@app.route("/qrcode", methods=["GET", "POST"])
def qrcode():
    #Generates the QR Code
    gen = GPQRGen("http://localhost:3000", flask.session["amount"])
    gpqrcode = gen.generate()
    qrcodeUUID = gen.getUUID()
    
    #Outputs the QR Code, ready to scan
    src = f"static/{qrcodeUUID}.png"
    return render_template("qrcode.html", source=src)

@app.route("/slackredirect", methods=["GET", "POST"])
def slackredirect():
    authcode = request.args.get("code")
    authresponse = json.loads(requests.get(f"https://slack.com/api/oauth.v2.access?client_id={client_id}&client_secret={clientSecret}&code={authcode}").content)
    accessToken = ""
    if authresponse["ok"]:
        accessToken = authresponse["authed_user"]["access_token"]
    else:
        redirect("/404")
    
    #Getting the user's info
    userresponse = json.loads(requests.get(f"https://slack.com/api/users.identity?token={accessToken}").content)
    if userresponse["ok"]:
        userid = userresponse["user"]["id"]
        username = userresponse["user"]["name"]
        flask.session["authdict"] = {
            "id": userid,
            "name": username
        }
        
        #Updating that the user has logged in before
        try:
            print(username)
            record = admin_base.match("Slack Tag", username)
            print(record)
        except KeyError:
            return redirect("/notadmin")
        
        admin_base.update(record["id"], {
            "Slack Tag": username,
            "Affiliation": record["fields"]["Affiliation"],
            "Logged In?": True
        })
    else:
        redirect("/404")
        
    #Taking user back to the generator page
    return redirect("/generate")

@app.route("/claim", methods=["GET", "POST"])
def claim():
    uuid = request.args.get("uuid")
    amount = request.args.get("amount")
    
    

if __name__ == '__main__': #this checks that it's actually you running main.py not an import
    app.run(host='0.0.0.0', debug=True, port=3000) #this tells flask to go