from flask import Flask, request, render_template, redirect
import flask
from qrgen import GPQRGen
from airtable import Airtable
import json
import requests
import os

# Getting environment variables
airtable_auth_key = os.environ["airtable_auth_key"]
base_key = os.environ["base_key"]
client_id = os.environ["client_id"]
clientSecret = os.environ["client_secret"]
secretKey = os.environ["secret_key"]
softbank_api_key = os.environ["softbank_api_key"]
qrgen_url = os.environ["qrgen_url"]

app = Flask(__name__)
app.secret_key = secretKey

# Airtable bases
claims_base = Airtable(base_key, "Coin Claims", api_key=airtable_auth_key)
admin_base = Airtable(base_key, "Verified Generators", api_key=airtable_auth_key)


@app.route("/", methods=["GET", "POST"])
def index():
    return ("This is the index.", 200)

#Admin start here!
@app.route("/generate", methods=["GET", "POST"])
def generate():
    # Making sure that admin has logged in before
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
    # Generates the QR Code
    gen = GPQRGen(qrgen_url, flask.session["amount"])
    gpqrcode = gen.generate()
    qrcodeUUID = gen.getUUID()

    # Outputs the QR Code, ready to scan
    src = f"static/{qrcodeUUID}.png"
    return render_template("qrcode.html", source=src)


@app.route("/admin-slackredirect", methods=["GET", "POST"])
def admin_slackredirect():
    authcode = request.args.get("code")
    authresponse = json.loads(requests.get(
        f"https://slack.com/api/oauth.v2.access?client_id={client_id}&client_secret={clientSecret}&code={authcode}").content)
    accessToken = ""
    if authresponse["ok"]:
        accessToken = authresponse["authed_user"]["access_token"]
    else:
        redirect("/404")

    # Getting the user's info
    userresponse = json.loads(requests.get(
        f"https://slack.com/api/users.identity?token={accessToken}").content)
    if userresponse["ok"]:
        userid = userresponse["user"]["id"]
        username = userresponse["user"]["name"]
        flask.session["authdict"] = {
            "id": userid,
            "name": username
        }

        # Updating that the user has logged in before
        try:
            print(username)
            record = admin_base.match("User ID", userid)
            print(record)
        except KeyError:
            return redirect("/notadmin")

        admin_base.update(record["id"], {
            "Logged In?": True
        })
    else:
        redirect("/404")

    # Taking user back to the generator page
    return redirect("/generate")


@app.route("/404", methods=["GET", "POST"])
def fourOfour():
    return ("404 Not Found", 404)


@app.route("/notadmin", methods=["GET", "POST"])
def notadmin():
    return ("You're not an admin; contact @Harshith on Hack Club Slack for more info.", 200)


@app.route("/slackredirect", methods=["GET", "POST"])
def user_slackredirect():
    authcode = request.args.get("code")
    authresponse = json.loads(requests.get(
        f"https://slack.com/api/oauth.v2.access?client_id={client_id}&client_secret={clientSecret}&code={authcode}").content)
    if authresponse["ok"]:
        accessToken = authresponse["authed_user"]["access_token"]
    else:
        redirect("/404")

    # Getting the user's info
    userresponse = json.loads(requests.get(
        f"https://slack.com/api/users.identity.email?token={accessToken}").content)
    if userresponse["ok"]:
        userid = userresponse["user"]["id"]
        username = userresponse["user"]["name"]
        userEmail = userresponse["user"]["email"]
        flask.session["user"]["authdict"] = {
            "id": userid,
            "name": username,
            "email": userEmail
        }
    else:
        return redirect("/404")

    # Taking user back to the generator page
    return redirect("/claimed")

#Users, once they scan their QR codes, end up here and go from here!
@app.route("/claim", methods=["GET", "POST"])
def claim():
    uuid = request.args.get("uuid")
    amount = request.args.get("amount")

    flask.session["user"]["uuid"] = uuid
    flask.session["user"]["amount"] = amount

    # Checking if the QR Code has been claimed already
    record = claims_base.match("UUID", uuid)
    if (record["fields"]["Claimant Slack Email"]):
        return redirect("/taken")

    return redirect("/user_slackredirect")


@app.route("/taken", methods=["GET", "POST"])
def taken():
    return ("This QR code has been scanned already, and as such, the gp has been claimed. Sorry!", 200)


@app.route("/claimed", methods=["GET", "POST"])
def claimed():
    # Updating the database that the user has claimed their prize
    userEmail = flask.session["user"]["authdict"]["email"]
    userId = flask.session["user"]["authdict"]["id"]
    uuid = flask.session["user"]["uuid"]
    # Getting the record of the matched uuid
    record = claims_base.match("UUID", uuid)
    # Updating the record with the collected email
    claims_base.update(record[id], {
        "UUID": uuid,
        "Amount": flask.session["user"]["amount"],
        "Claimant Slack Email": userEmail
    })

    # The bot gives all the currencies to the user
    requests.post("https://softbank.codered.cloud/hackcoin/redeem", {
        "auth": softbank_api_key,
        "amount": flask.session["user"]["amount"],
        "user": userId
    })

    # Done
    return ("Done! Check Slack for your new gp!", 200)


if __name__ == '__main__':  # this checks that it's actually you running main.py not an import
    app.run(host='0.0.0.0', debug=False, port=3000)  # this tells flask to go
