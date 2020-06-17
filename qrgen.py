import qrcode
import uuid
import requests
import json
from airtable import Airtable

#Getting config stuff
with open("config.json") as f:
    config = json.load(f);
    airtable_auth_key = config["airtable_auth_key"]
    base_key = config["base_key"] 

class GPQRGen():
    def __init__(self, domain, amount=20):
        self.newUUID = str(uuid.uuid4())
        
        #Writes the info to the Airtable base
        airtable = Airtable(base_key, "Coin Claims", api_key=airtable_auth_key)
        record = {
            "UUID": self.newUUID,
            "Amount": amount,
            "Claimant Slack Email": ""
        }
        airtable.insert(record)
        
        #Creating the link
        self.link = f"{domain}/claim?uuid={self.newUUID}&amount={amount}"
    
    def getlink(self):
        return self.link

    def getUUID(self):
        return self.newUUID
    
    def generate(self):
        img = qrcode.make(self.getlink())
        img.save(f"static/{self.getUUID()}.png")