from os import environ
from datetime import date, timedelta
from get_mishna import main as get_mishna_main
from is_yomtov import is_holiday

today = date.today()
tomorrow = today + timedelta(days=1)

def main():
    if is_holiday(today):
        print("Today is a holiday!")
        return
    if "NOON" in environ and is_holiday(tomorrow):
        print("Tomorrow is a holiday!")
        return
    get_mishna_main()


if __name__ == "__main__":
    main()
