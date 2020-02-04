# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (c) 2019, James Miller
# Copyright (c) 2019, Peter Levi <peterlevi@peterlevi.com>
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

from locale import gettext as _

import requests

from variety.plugins.IQuoteSource import IQuoteSource


class UrbanDictionarySource(IQuoteSource):
    @classmethod
    def get_info(cls):
        return {
            "name": "Urban Dictionary",
            "description": _("Displays definitions from Urban Dictionary"),
            "author": "James Miller",
            "version": "0.1",
        }

    def get_random(self):
        dict_dict = requests.get("https://api.urbandictionary.com/v0/random").json()

        def _clean(s):
            return s.strip().replace("[", "").replace("]", "")

        result = []
        for entry in dict_dict["list"]:
            word = entry["word"]
            definition = _clean(entry["definition"])
            example = _clean(entry["example"])
            quote = (
                '"{}"'.format(word)
                + "\n\n"
                + definition
                + ("\n\nExample:\n{}".format(example) if example else "")
            )

            result.append(
                {
                    "quote": quote,
                    "author": entry["author"],
                    "sourceName": "Urban Dictionary",
                    "link": entry["permalink"],
                }
            )

        return result
