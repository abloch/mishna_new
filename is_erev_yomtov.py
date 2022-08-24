from datetime import date, timedelta
import requests
from sys import exit
from pprint import pformat
from sys import argv
import telepot
import json

tomorrow = date.today() + timedelta(days=1)
url = f"https://www.hebcal.com/hebcal?v=1&cfg=json&maj=on&mod=on&nx=off&year={tomorrow.year}&month={tomorrow.month}&ss=on&c=on&city=IL-Jerusalem&i=on"
reply = requests.get(url).json()

config = json.load(open(argv[1]))

def send_to_telegram(message, group):
    token = config["TELEGRAM_TOKEN"]
    bot = telepot.Bot(token)
    bot.sendMessage(group, message)

relevant = [item for item in reply['items'] if item.get("date") == tomorrow.isoformat()]
if relevant:
    yomtov = any(item.get("yomtov") for item in relevant)
    msg = {"today is": relevant, "yomtov": yomtov}
    send_to_telegram(pformat(msg), 215513269)
    if yomtov:
        exit(1)
