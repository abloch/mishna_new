from datetime import date
import requests
from sys import exit
from pprint import pformat
from sys import argv
from get_mishna import send_to_telegram, parse_config

def is_holiday(inspection_date, tisha_beav_as_holiday=True):
    url = f"https://www.hebcal.com/hebcal?v=1&cfg=json&maj=on&mod=on&nx=off&year={inspection_date.year}&month={inspection_date.month}&ss=on&c=on&city=IL-Jerusalem&i=on"

    reply = requests.get(url).json()

    config = parse_config()
    relevant = [item for item in reply['items'] if item.get("date") == inspection_date.isoformat()]
    if relevant:
        tbav = any(item.get("hebrew") == "תשעה באב" for item in relevant)
        if tisha_beav_as_holiday and tbav:
            send_to_telegram(config, "inspection_date is Tisha B'Av", 215513269)
            return True
        yomtov = any(item.get("yomtov") for item in relevant)
        msg = {"inspection_date is": relevant, "yomtov": yomtov}
        send_to_telegram(config, pformat(msg), 215513269)
        return bool(yomtov)
    return False

if __name__ == "__main__":
    main()
