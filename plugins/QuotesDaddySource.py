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

from variety.Util import Util
from variety.plugins.IQuoteSource import IQuoteSource

import logging
logger = logging.getLogger("variety")

class QuotesDaddySource(IQuoteSource):
    @classmethod
    def get_info(cls):
        return {
            "name": "Quotes from QuotesDaddy",
            "description": "Fetches quotes from QuotesDaddy's daily quotes RSS feed",
            "author": "Peter Levi",
            "version": "0.1"
        }

    def supports_search(self):
        return False

    def get_random(self):
        url = "http://www.quotesdaddy.com/feed"

        bs = Util.xml_soup(url)
        item = bs.find("item")
        if not item:
            logger.warning("Could not find quotes for URL " + url)
            return None
        link = item.find("link").contents[0].strip()
        s = item.find("description").contents[0]
        author = s[s.rindex('- ') + 1:].strip()
        quote = s[:s.rindex('- ')].strip().replace('"', '').replace('<br>', '\n').replace('<br/>', '\n').strip()
        quote = u"\u201C%s\u201D" % quote

        return [{"quote": quote, "author": author, "sourceName": "QuotesDaddy", "link": link}]
