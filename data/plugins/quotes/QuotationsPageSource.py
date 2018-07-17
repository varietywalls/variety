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

import bs4
import random
import re

from variety.Util import Util
from variety.plugins.IQuoteSource import IQuoteSource
from httplib2 import iri2uri
from variety import _, _u
import logging

logger = logging.getLogger("variety")


class QuotationsPageSource(IQuoteSource):
    @classmethod
    def get_info(cls):
        return {
            "name": "TheQuotationsPage.com",
            "description": _("Fetches quotes from TheQuotationsPage.com"),
            "author": "Peter Levi",
            "version": "0.1"
        }

    def supports_search(self):
        return True

    def get_from_html(self, url, html):
        quotes = []
        bs = bs4.BeautifulSoup(html)
        fixmap = {
            '\u0091': "\u2018",
            '\u0092': "\u2019",
            '\u0093': "\u201C",
            '\u0094': "\u201D",
            '\u0085': "...",
            '\u0097': "\u2014",
            '\u0096': "-"
        }
        for item in bs.findAll('dt', 'quote'):
            quote = None
            try:
                quote = item.find('a').contents[0]
                for k, v in list(fixmap.items()):
                    quote = quote.replace(k, v)
                quote = "\u201C%s\u201D" % quote
                link = "http://www.quotationspage.com" + item.find('a')['href']
                try:
                    author = item.next_sibling.find('b').find('a').contents[0]
                except Exception:
                    try:
                        author = item.next_sibling.find('b').contents[0]
                    except Exception:
                        author = None

                quotes.append({"quote": quote, "author": author, "sourceName": "TheQuotationsPage.com", "link": link})
            except Exception:
                logger.warning(lambda: "Could not get or parse quote: %s" % quote)

        if not quotes:
            logger.warning(lambda: "QuotationsPage: no quotes found at %s" % url)

        return quotes

    def get_random(self):
        return self.get_for_search_url("http://www.quotationspage.com/random.php3")

    def get_for_author(self, author):
        return self.get_for_search_url(
            iri2uri(("http://www.quotationspage.com/search.php3?Search=&Author=%s" % author).encode('utf-8')))

    def get_for_keyword(self, keyword):
        return self.get_for_search_url(
            iri2uri(("http://www.quotationspage.com/search.php3?Search=%s&Author=" % keyword).encode('utf-8')))

    def get_for_search_url(self, url):
        logger.info(lambda: "Fetching quotes from Goodreads for search url=%s" % url)
        html = Util.fetch(url)
        try:
            page = random.randint(1, int(re.findall('Page 1 of (\d+)', html)[0]))
            url += "&page=%d" % page
            html = Util.fetch(url)
        except Exception:
            pass # probably just one page

        logger.info(lambda: "Used QuotationsPage url %s" % url)

        r = r'.*<dl>(.*)</dl>.*'
        if re.match(r, html, flags=re.M | re.S):
            html = re.sub(r, '<html><body>\\1</body></html>', html, flags=re.M | re.S)
            # without this BeautifulSoup gets confused by some scripts

        return self.get_from_html(url, html)


if __name__ == "__main__":
    q = QuotationsPageSource()
    print(q.get_for_author("einstein"))
    print(q.get_for_keyword("funny"))
    print(q.get_random())
