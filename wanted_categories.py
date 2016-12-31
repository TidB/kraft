import requests

import api
from config import CONFIG

LANGUAGES = ["", "ar", "cs", "da", "de", "es", "fi", "fr", "hu", "it", "ja", "ko", "nl", "no", "pl", "pt", "pt-br", "ro", "ru", "sv", "tr", "zh-hans", "zh-hant"]

session = requests.Session()
session.headers["User-Agent"] = "Enhanced Reports (TidB)"
edit_api = api.API("https://wiki.teamfortress.com/w/api.php")

wanted_categories = session.get(
    "https://wiki.teamfortress.com/w/api.php",
    params={
        "action": "query",
        "format": "json",
        "list": "querypage",
        "qppage": "Wantedcategories",
        "qplimit": "max",
    }
).json()

categories = wanted_categories["query"]["querypage"]["results"]  # Unnesting

slots = {}
for category in categories:
    title = category["title"]
    if "/" in title:
        end = title.split("/")[1]
    else:
        end = ""

    if end in slots:
        slots[end].append(title)
    else:
        slots[end] = [title]


"""End layout:

{{Languages|User:TidB/WantedCategories}}

<code>
[[:Category:Bla]]

[[:Category:Blubb]]

.
.
.

[[Category:Whatever]]
</code>
"""

edit_api.login(CONFIG["username"], CONFIG["password"])
edit_api.get_edit_token()

for language in LANGUAGES:
    text = "{{Languages|User:TidB/WantedCategories}}\n\n"

    if language == "":
        site = "User:TidB/WantedCategories"
    else:
        site = "User:TidB/WantedCategories/{}".format(language)

    if language in slots:  # There are categories missing
        link_list = "]]\n\n[[:".join(sorted(slots[language]))
        text = (
            text +
            "<code>\n[[:" +
            link_list +
            "]]\n</code>"
        )

        if language == "ar":
            text = text.join(['<div dir="ltr">\n', "\n</div>"])
    else:  # No categories missing
        text = "".join([text, "Everything's alright."])

    edit_api.edit(site, text, "Updated")
