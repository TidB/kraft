import requests

import api
from config import CONFIG

LANGUAGES = ("", "ar", "cs", "da", "de", "es", "fi", "fr", "hu", "it", "ja",
             "ko", "nl", "no", "pl", "pt", "pt-br", "ro", "ru", "sv", "tr",
             "zh-hans", "zh-hant")

session = requests.Session()
session.headers["User-Agent"] = "Enhanced Reports (TidB)"
edit_api = api.API("https://wiki.teamfortress.com/w/api.php")

cont = True
offset = 0

edit_api.login(CONFIG["username"], CONFIG["password"])
edit_api.get_edit_token()

slots = {}
while cont:
    print("Retrieving with offset", offset, "...")
    wanted_pages = edit_api.get(
        "https://wiki.teamfortress.com/w/api.php",
        params={
            "action": "query",
            "format": "json",
            "list": "querypage",
            "qppage": "Wantedpages",
            "qplimit": "max",
            "continue": "-||",
            "qpoffset": offset,
        }
    )
    print("Retrieved successfully.")

    pages = wanted_pages["query"]["querypage"]["results"]  # Unnesting

    # TODO: Check if it's a localized page
    for page in pages:
        title = page["title"]
        value = page["value"]
        if "/" in title:
            e = title.rsplit("/")[1]
            if e in LANGUAGES:
                end = e
            else:
                end = ""
        else:
            end = ""

        if end in slots:
            slots[end].append((title, value))
        else:
            slots[end] = [(title, value)]

    print("slots:\n", slots)
    if "continue" not in wanted_pages:
        cont = False
    else:
        offset = wanted_pages["continue"]["qpoffset"]
        print("New offset:", offset)

"""End layout:

{{Languages|User:TidB/WantedPages}}

<code>
[[Page]] (123)

[[Page2]] (45)

.
.
.

[[Whatever]] (3)
</code>
"""

#edit_api.login(CONFIG["username"], CONFIG["password"])
#edit_api.get_edit_token()

for language in LANGUAGES:
    text = "{{Languages|User:TidB/WantedPages}}\n\n"

    if language == "":
        site = "User:TidB/WantedPages"
    else:
        site = "User:TidB/WantedPages/{}".format(language)

    if language in slots:  # There are wanted pages
        link_list = "\n\n".join(
            "[[:{0}]] ({1})".format(i, j)
            for i, j
            in sorted(slots[language], key=lambda x: int(x[1]), reverse=True)
        )
        text = (
            text +
            "<code>\n" +
            link_list +
            "\n</code>"
        )

    else:  # No wanted pages (never gonna happen)
        text = "".join([text, "Everything's alright."])

    if language == "ar":
            text = text.join(['<div dir="ltr">\n', "\n</div>"])

    with open("r"+language, "wb") as f:
        f.write(bytes(text, "utf-8"))
    #edit_api.edit(site, text, "Updated.")
