from get_mishna import *

masechet, chapter, mishna = deserialize()
while True:
    masechet, chapter, mishna = get_next_mishna(masechet, chapter, mishna)
    print(masechet, chapter, mishna)
    print(get_mishna(masechet, chapter, mishna).strip())
    input("press enter to get next")
