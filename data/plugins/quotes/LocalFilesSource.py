# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (c) 2012, Peter Levi <peterlevi@peterlevi.com>
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
import logging
import os
import re

from variety import _
from variety.plugins.IQuoteSource import IQuoteSource

logger = logging.getLogger("variety")


class LocalFilesSource(IQuoteSource):
    def __init__(self):
        super(IQuoteSource, self).__init__()
        self.quotes = []

    @classmethod
    def get_info(cls):
        return {
            "name": "Local text files",
            "description": _(
                "Displays quotes, defined in local text files.\n"
                "Put your own txt files in: ~/.config/variety/pluginconfig/quotes/.\n"
                "The file format is:\n\nquote -- author\n.\nsecond quote -- another author\n.\netc...\n\n"
                "Example: http://rvelthuis.de/zips/quotes.txt"
            ),
            "author": "Peter Levi",
            "version": "0.1",
        }

    def supports_search(self):
        return True

    def activate(self):
        if self.active:
            return

        super(LocalFilesSource, self).activate()

        self.quotes = []

        # prefer files in the pluginconfig
        for f in os.listdir(self.get_config_folder()):
            if f.endswith(".txt"):
                self.load(os.path.join(self.get_config_folder(), f))

        # use the defaults if nothing useful in pluginconfig
        if not self.quotes:
            for f in os.listdir(self.folder):
                if f.endswith(".txt"):
                    self.load(os.path.join(self.folder, f))

    def deactivate(self):
        self.quotes = []

    def load(self, path):
        try:
            logger.info(lambda: "Loading quotes file %s" % path)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                s = f.read()
                for q in re.split(r"(^\.$|^%$)", s, flags=re.MULTILINE):
                    try:
                        if q.strip() and len(q.strip()) > 5:
                            parts = q.split("-- ")
                            quote = parts[0]
                            if quote[0] == quote[-1] == '"':
                                quote = "\u201C%s\u201D" % quote[1:-1]
                            author = parts[1].strip() if len(parts) > 1 else None
                            self.quotes.append(
                                {
                                    "quote": quote,
                                    "author": author,
                                    "sourceName": os.path.basename(path),
                                }
                            )
                    except Exception:
                        logger.debug(lambda: "Could not process local quote %s" % q)
        except Exception:
            logger.exception(lambda: "Could not load quotes file %s" % path)

    def get_random(self):
        return self.quotes

    def get_for_author(self, author):
        return [
            q for q in self.quotes if q["author"] and q["author"].lower().find(author.lower()) >= 0
        ]

    def get_for_keyword(self, keyword):
        return self.get_for_author(keyword) + [
            q for q in self.quotes if q["quote"].lower().find(keyword.lower()) >= 0
        ]
