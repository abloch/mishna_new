import re
import json
from bs4 import BeautifulSoup
import requests
import telepot
from functools import lru_cache
from sys import argv
from requests.adapters import HTTPAdapter, Retry

mishna_pattern = r"<.+?>"
mishna_re = re.compile(mishna_pattern)
mishna_pattern = r"\<[^\<]*"
commentary_re = re.compile(r"\{\{הע-שמאל\|(.*?)\}\}")
non_commentary_re = re.compile(r"\}\}(.*)")
link_pattern = r"\[\[(.*?)\|(.*?)\]\]"
link_re = re.compile(link_pattern)
quotes_re = re.compile(r"\((.*?)\)")
explanation_pattern = r"\{\{ב|מגירה\|(.*?)\|(.*?)\}\}"
explanation_re = re.compile(explanation_pattern)
title_pattern = re.compile(r"\=\=\=[^=]*?===")

config = json.load(open(argv[1]))

s = requests.Session()
s.mount("https://", HTTPAdapter(max_retries=Retry(total=50, backoff_factor=1.1)))

def get_wikisource_page(page:str, html_ver:bool=False):
    url = f"https://he.wikisource.org/w/api.php?action=parse&page={page}&format=json"
    print(url)
    if not html_ver:
        url = url + '&prop=wikitext'
    # print(url)
    return s.get(url).json()['parse']['text' if html_ver else 'wikitext']['*']

def get_variated_masechet(name):
	VARIATIONS = {
		"בכורים": "ביכורים",
        "ערובין": "עירובין",
	}
	return VARIATIONS.get(name, name)

def get_unvariated_masechet(name):
	VARIATIONS = {
		"ביכורים": "בכורים",
        "עירובין": "ערובין",
	}
	return VARIATIONS.get(name, name)


@lru_cache(maxsize=1024)
def get_sefaria_url(masechet, chapter, mishna):
    title = f"משנה_{masechet}_{chapter}_{mishna}"
    url = f"https://www.sefaria.org.il/api/name/{title}"
    name_reply = s.get(url).json()
    if not name_reply['is_ref']:
        raise RuntimeError(f"{title} is not a reference")
    return name_reply['url']

@lru_cache(maxsize=1024)
def get_sefaria(masechet, chapter, mishna):
    url = get_sefaria_url(masechet, chapter, mishna)
    return s.get(f"https://www.sefaria.org.il/api/texts/{url}").json()

def boldize(text):
    return "\n".join([f"*{line.strip()}*" for line in text.split("\n")])

def codize(text):
    stripped = "\n".join([l.strip() for l in text.split("\n")])
    return f"```{stripped}```"

def italize(text):
    return "\n".join([f"_{line.strip()}_" for line in text.split("\n")])

def underline(text, double=False):
    char = '͟' if double else '̲'
    return codize(char.join(f" {text} ")) + "\n"

def get_all_chapter_page(masechet, chapter):
    title = f"ביאור:משנה_{masechet}_פרק_{chapter}"
    return get_wikisource_page(title)

def get_mishna_part(text, mishna):
    return re.findall(f"<קטע התחלה\={mishna}/>(.*)<קטע סוף={mishna}/>", text)

def get_commentary(masechet, chapter, mishna):
    html = get_mishna_part(masechet, chapter, mishna)
    soup = BeautifulSoup(html, features='html.parser')
    parts = soup.find_all("small")
    return [part.parent.parent.text.split("\xa0") for part in parts if hasattr(part, 'text')]

def get_explanations(masechet, chapter, mishna):
    html = get_mishna_part(masechet, chapter, mishna)
    soup = BeautifulSoup(html, features='html.parser')
    return [td.text.strip() for td in soup.find_all("table") if hasattr(td, 'text')]
    
def commentize(commetraies):
    return "\n".join([f"*{c[0].strip()}* - _{c[1].strip()}_" for c in commetraies])

def get_commentary_url(masechet, chapter, mishna):
    wikitext = f"https://he.wikisource.org/wiki/משנה_{masechet}_{chapter}_{mishna}"
    sefaria_ref = get_sefaria_url(masechet, chapter, mishna)
    bartenura = f"https://www.sefaria.org.il/{sefaria_ref}?lang=he&with=Bartenura&lang2=he"
    rambam = f"https://www.sefaria.org.il/{sefaria_ref}?lang=he&with=Rambam&lang2=he"
    shimshom = f"https://he.wikisource.org/wiki/רבינו_שמשון_על_{masechet}_{chapter}#משנה_{mishna}"
    toyt = f'https://www.sefaria.org.il/Tosafot_Yom_Tov_on_{sefaria_ref}?lang=he'
    mevoeret = f"https://he.wikisource.org/wiki/ביאור:משנה_{masechet}_פרק_{chapter}#משנה_{mishna}"
    return {
        # "דף פרשנים": wikitext,
        "ברטנורא": bartenura,
        'רמב"ם': rambam,
        # "רבנו שמשון": shimshom,
        # 'תוי"ט': toyt,
        'ויקיטקסט': mevoeret,
    }

def explanaize(texts):
    return "\n".join([text for text in texts])

@lru_cache(maxsize=2048)
def get_mishna_part(masechet, chapter, mishna):
    url = f"ביאור:משנה_{get_unvariated_masechet(masechet)}_פרק_{chapter}"
    all_text = get_wikisource_page(url, True)
    soup = BeautifulSoup(all_text, features='html.parser')
    el = soup.find("div", {"id": f"משנה_{mishna}"})
    elements = [el]
    if el is None:
        raise f"could not parse {el}"
    for i in el.next_siblings:
        if i.name=='div' and i.get("id", "").startswith("משנה_"):
            break
        # if hasattr(i, 'text'):
        elements.append(i)
    return "".join([i.decode_contents() for i in elements if hasattr(i, 'decode_contents')])

def get_mishna_text(masechet, chapter, mishna):
    sefaria = get_sefaria(masechet, chapter, mishna)
    section = sefaria['toSections'][-1] - 1
    return sefaria['he'][section].strip().replace(".", ".\n")

def get_mishna_title(masechet, chapter, mishna):
    return f"מסכת {masechet} {chapter};{mishna}"

def get_mishna(masechet, chapter, mishna):
    ret = underline(get_mishna_title(masechet, chapter, mishna))
    ret += boldize(get_mishna_text(masechet, chapter, mishna)) + "\n\n"
    commentary = get_commentary(masechet, chapter, mishna) 
    if commentary:
        ret += underline("משנה מבוארת")
        ret += commentize(commentary) + "\n\n"
    ret += underline("פרשנים")
    for parshan, link in get_commentary_url(masechet, chapter, mishna).items():
        ret += f"*{parshan}*: - {link}\n"
    explanations = get_explanations(masechet, chapter, mishna)
    if explanations:
        ret +='\n\n' + underline("הרחבה")
        ret += "\n\n".join([italize(expl) for expl in explanations])
    return ret

def send_to_whatsapp(message):
    whatsmate_url = "https://gate.whapi.cloud/messages/text"
    headers = {
            "Authorization": config["WHAPI_AUTH"],
    }
    payload = {
        "to": config["MISHNA_GROUP"],
        "body": message,
    }
    resp = s.post(whatsmate_url, headers=headers, json=payload).json()
    print(resp)

def send_to_telegram(message, group="@mishna"):
    if config["DRY_RUN"]:
        group = 215513269
    token = config["TELEGRAM_TOKEN"]
    bot = telepot.Bot(token)
    bot.sendMessage(group, message)

def send_all(masechet, chapter, mishna):
    out = get_mishna(masechet, chapter, mishna).strip()
    if not config.get("LOCAL"):
        send_to_whatsapp(out)
        send_to_telegram(out)
    open("mishna.txt", "w").write(out)

def get_next_mishna(masechet, chapter, mishna):
    title = f"משנה_{get_variated_masechet(masechet)}_{chapter}_{mishna}"
    url = f"https://he.wikisource.org/w/api.php?action=query&prop=revisions&rvprop=content&rvsection=0&titles={title}&format=json&rvslots=*"
    print(url)
    reply = s.get(url).json()
    metadata = next(iter(reply["query"]["pages"].values()))["revisions"][0]["slots"]["main"]["*"]
    if metadata is None:
        raise f"{url} is malformed"
    parts = re.search(r"\{\{(.*?)\}\}", metadata).group(1).split("|")
    next_mishna = parts[6]
    *masechet, chapter, mishna = next_mishna.split(" ")
    return " ".join(masechet), chapter, mishna

def serialize(masechet, chapter, mishna):
    filename = config['SERIALZIZATION_FILENAME']
    payload = {
        "masechet": masechet, "chapter": chapter, "mishna": mishna
    }
    json.dump(payload, open(filename, "w"), ensure_ascii=False)

def deserialize():
    filename = config['SERIALZIZATION_FILENAME']
    payload = json.load(open(filename))
    return payload['masechet'], payload['chapter'], payload['mishna']

def main():
    masechet, chapter, mishna = deserialize()
    # send_all(masechet, chapter, mishna)
    masechet, chapter, mishna = get_next_mishna(masechet, chapter, mishna)
    serialize(masechet, chapter, mishna)

if __name__ == "__main__":
    main()
