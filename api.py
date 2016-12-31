from collections import OrderedDict
from sys import stderr
from time import sleep
from traceback import format_exc

import mwparserfromhell
import requests

from helpers import chunker, show_progress


def safe_request(request, api_location, **kwargs):
    """Encapsulates a request like request.post or request.get into a retry
    block. Requires the request to be a object in the JSON form. Returns
    the JSON object."""
    retry = True
    while retry:
        try:
            response = request(api_location, **kwargs)
            response = response.json()
            if "error" in response:
                print("Code:", response["error"]["code"], "\n",
                      "Info:", response["error"]["info"], file=stderr)
            else:
                retry = False
        except Exception:
            print(format_exc(), file=stderr)

    return response


class API:
    def __init__(self, api_location, session=None):
        self.api_location = api_location
        self.edit_token = None

        if session is None:
            self.session = requests.Session()
        else:
            self.session = session

    def get(self, api_location, **kwargs):
        return safe_request(self.session.get, api_location, **kwargs)

    def post(self, api_location, **kwargs):
        return safe_request(self.session.post, api_location, **kwargs)

    def login(self, name, password):
        login_params = {
            "action": "login",
            "format": "json",
            "lgname": name,
            "lgpassword": password
        }

        response = self.post(self.api_location, params=login_params, verify=True)
        print("Got response", response)
        login_params["lgtoken"] = response["login"]["token"]

        response = self.post(self.api_location, params=login_params, verify=True)
        print("Got response", response)

    def get_edit_token(self):
        token_params = {
            "action": "query",
            "format": "json",
            "meta": "tokens",
        }
        response = self.post(self.api_location, params=token_params, verify=True)
        print("Got response", response)
        self.edit_token = response["query"]["tokens"]["csrftoken"]

    def edit(self, title, text, summary):
        edit_params = {
            "format": "json",
            "action": "edit",
            "title": title,
            "summary": summary,

        }

        edit_data = {
            "text": text,
            "token": self.edit_token,
        }
        return self.post(self.api_location, params=edit_params, data=edit_data, verify=True)

    def retrieve_pagelist(self, language):
        show_progress(0, 1, "Retrieving pagelist...")
        all_pages = self.get(self.api_location, params={
            "action": "query",
            "format": "json",
            "redirects": "",
            "prop": "revisions",
            "rvprop": "content",
            "rvsection": "1",
            "titles": "Team Fortress Wiki:Reports/All articles/{}".format(
                language
            )
        })

        page_query = list(all_pages["query"]["pages"].values())[0]
        page_query = page_query["revisions"][0]["*"]
        language_pagelist = [page[4:-2] for page in page_query.splitlines()[1:]]
        show_progress(1, 1, "Retrieved pagelist.", True)
        return language_pagelist

    def retrieve_pages(self, pagetitles, data, chunk_size, delay):
        chunks = chunker(pagetitles, chunk_size)
        for i, chunk in enumerate(chunks):
            show_progress(
                i * chunk_size + len(chunk), len(pagetitles),
                "Retrieving chunk '{}'-'{}'".format(chunk[0], chunk[-1])
            )
            data["titles"] = "|".join(chunk)
            response = self.post(self.api_location, data=data)
            if "warnings" in response:
                print("\tWarning\n", response["warnings"],
                      "\nChunk =", chunk,
                      file=stderr)

            yield response
            sleep(delay)

        show_progress(len(pagetitles), len(pagetitles),
                      "Retrieved chunks.", True)
