from collections import OrderedDict
from difflib import HtmlDiff
import webbrowser
import time

import mwparserfromhell as mw
import requests

import api
from config import CONFIG

LANGUAGES = ["en", "ar", "cs", "da", "de", "es", "fi", "fr", "hu", "it", "ja",
             "ko", "nl", "no", "pl", "pt", "pt-br", "ro", "ru", "sv", "tr",
             "zh-hans", "zh-hant"]
DIFF_FILE = "diff.html"


def main():
    """Update the {translation switching} templates on the templates or their
    doc pages."""
    template_titles = template_titles_from_category("Templates that use translation switching")
    doc_template_titles = template_titles_from_category("Template documentation")

    regular_template_titles = list(filter(
        lambda x: not x.endswith("/doc"),
        template_titles
    ))

    print("# of regular templates:", len(regular_template_titles))
    print("# of doc templates:", len(doc_template_titles))

    templates = get_template_contents(regular_template_titles)
    doc_templates = get_template_contents(doc_template_titles)

    edit_api.login(CONFIG["username"], CONFIG["password"])
    edit_api.get_edit_token()

    for title, content in templates.items():
        curr_content = str(content)
        supported_languages = check_translations(content)
        doc_title = title+"/doc"
        if doc_title in doc_template_titles:
            doc_content = doc_templates[doc_title]
        else:
            doc_content = None
        new_content, use_doc = update_translation_switching(
            content, doc_content, supported_languages
        )
        if use_doc:
            edit_page(doc_title, str(new_content), doc_templates[doc_title])
        else:
            edit_page(title, str(new_content), curr_content)


def main_reports():
    """For each language, create a page listing templates where this language
    is not fully supported via translation switching yet."""
    template_titles = template_titles_from_category(
        "Templates that use translation switching")

    regular_template_titles = list(filter(
        lambda x: not x.endswith("/doc"),
        template_titles
    ))

    print("# of regular templates:", len(regular_template_titles))

    templates = get_template_contents(regular_template_titles)

    edit_api.login(CONFIG["username"], CONFIG["password"])
    edit_api.get_edit_token()

    slots = dict.fromkeys(LANGUAGES, "")
    for title, content in templates.items():
        supported_languages = check_translations(content)
        for language in slots:
            if language not in supported_languages:
                slots[language] += "* {{tl|"+title[9:]+"}}\n"

    for language, text in slots.items():
        text = "{{Languages|User:TidB/Missing translations}}\n\n"+text

        if language in ["en", ""]:
            site = "User:TidB/Missing translations"
        else:
            site = "User:TidB/Missing translations/{}".format(language)

        if language == "ar":
            text = text.join(['<div dir="ltr">\n', "\n</div>"])

        edit_api.edit(site, text, "Updated")


def template_titles_from_category(category_name):
    """Get all page titles inside the 'Template' namespace from a category.
    Ignores sandboxes."""
    continue_ = True
    cmcontinue = ""
    all_titles = []
    while continue_:
        template_titles = edit_api.get(
            "https://wiki.teamfortress.com/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "list": "categorymembers",
                "cmtitle": "Category:{}".format(category_name),
                "cmdir": "asc",
                "cmlimit": "max",
                "continue": "-||",
                "cmcontinue": cmcontinue,
            }
        )

        if "continue" in template_titles:
            cmcontinue = template_titles["continue"]["cmcontinue"]
        else:
            continue_ = False

        all_titles.extend([page["title"]
                           for page in
                           template_titles["query"]["categorymembers"]
                           if page["title"].startswith("Template:") and
                           not page["title"].lower().endswith("/sandbox")])

    return all_titles


def get_template_contents(template_titles):
    templates = dict()
    template_contents = edit_api.retrieve_pages(
        template_titles,
        data={
            "action": "query",
            "format": "json",
            "prop": "revisions|transcludedin",
            "rvprop": "content",
            "tilimit": 500,
            "tinamespace": 0,
        },
        chunk_size=50,
        delay=0
    )

    for chunk in template_contents:
        for page in chunk["query"]["pages"].values():
            title = page["title"]
            if (not title.startswith("Template:")) and (not title.endswith("/doc")):  # Ensure we're only using the template namespace
                continue
            templates[page["title"]] = mw.parse(page["revisions"][0]["*"])

    return OrderedDict(sorted(templates.items()))


def check_translations(template):
    """Check what languages are supported in the given template.

    Params:
      template (mw.Wikicode)"""
    # Assume this template supports every language
    languages = set(LANGUAGES)
    for switching in template.ifilter_templates(
            matches=lambda x: x.name.matches("lang")
    ):
        template_languages = {param.name.strip()
                              for param in switching.params
                              if param.name.strip() in LANGUAGES
                              }

        # Every language not defined is removed
        languages &= template_languages
    languages = sorted(languages)
    if "en" in languages:
        languages.remove("en")
        languages.insert(0, "en")
    return languages if languages else ["none"]


def update_translation_switching(template, doc_template, languages):
    """Update the appropriate translation switching template with the pro-
    vided languages.

    Params:
      template (mw.Wikicode)
      doc_template (mw.Wikicode)
      languages (list[str])"""
    info_template = template.filter_templates(
        matches=lambda x: x.name.matches("translation switching") or x.name.matches("ts")
    )

    if info_template:
        info_template = info_template[0]
        use_doc = False
    else:
        info_template = doc_template.filter_templates(
            matches=lambda x: x.name.matches("translation switching") or x.name.matches("ts")
        )
        if info_template:
            info_template = info_template[0]
            use_doc = True
        else:
            raise ValueError("No translation switching template could be found")

    if info_template.has(1):
        info_template.get(1).value = ", ".join(languages)
    else:
        info_template.add(1, ", ".join(languages))

    return doc_template if use_doc else template, use_doc


def edit_page(title, content, curr_content):
    print("Editing template", title)
    with open(DIFF_FILE, "w", encoding="utf-8") as file:
        file.write(HtmlDiff().make_file(str(curr_content).splitlines(), content.splitlines()))
    webbrowser.open(DIFF_FILE)
    edit = input("Accept changes and edit page y/n? ").lower().strip()
    if edit == "y":
        edit_api.edit(title, content, "Updated available languages")
    else:
        print("Edit discarded")


if __name__ == "__main__":
    session = requests.Session()
    session.headers["User-Agent"] = "Enhanced Reports (TidB)"
    edit_api = api.API("https://wiki.teamfortress.com/w/api.php")
    #main()  # Currently not safe enough and also not really needed that much
    main_reports()
