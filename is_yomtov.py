from datetime import date
import requests
from sys import exit
from pprint import pformat
from sys import argv
import telepot
import json

today = date.today()
url = f"https://www.hebcal.com/hebcal?v=1&cfg=json&maj=on&mod=on&nx=off&year={today.year}&month={today.month}&ss=on&c=on&city=IL-Jerusalem&i=on"
reply = requests.get(url).json()

config = json.load(open(argv[1]))


def send_to_telegram(message, group):
    token = config["TELEGRAM_TOKEN"]
    bot = telepot.Bot(token)
    bot.sendMessage(group, message)


relevant = [item for item in reply['items'] if item.get("date") == today.isoformat()]
if relevant:
    tbav = any(item.get("hebrew") == "תשעה באב" for item in relevant)
    if tbav:
        send_to_telegram("Today is Tisha B'Av", 215513269)
        exit(1)
    yomtov = any(item.get("yomtov") for item in relevant)
    msg = {"today is": relevant, "yomtov": yomtov}
    send_to_telegram(pformat(msg), 215513269)
    if yomtov:
        exit(1)
