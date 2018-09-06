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

import random
import re
from httplib2 import iri2uri
from variety.Util import Util
from variety.plugins.IQuoteSource import IQuoteSource
from variety import _

import logging

logger = logging.getLogger("variety")

KEYWORDS = [
    'love', 'humor', 'inspirational', 'life', 'funny', 'writing', 'death', 'romance', 'truth', 'poetry',
    'religion', 'god', 'philosophy', 'wisdom', 'books', 'happiness', 'humour', 'art', 'faith', 'politics',
    'reading', 'science', 'relationships', 'war', 'inspiration', 'friendship', 'women', 'music', 'success',
    'hope', 'spirituality', 'freedom', 'fear', 'beauty', 'christianity', 'history', 'inspirational-quotes',
    'time', 'marriage', 'fantasy', 'dreams', 'sex', 'nature', 'education', 'life-lessons', 'change',
    'literature', 'children', 'pain', 'fiction', 'money', 'people', 'knowledge', 'motivational', 'family',
    'humanity', 'peace', 'reality', 'kindlehighlight', 'self-help', 'men', 'courage', 'society', 'creativity',
    'power', 'humorous', 'future', 'food', 'heart', 'quotes', 'work', 'words', 'memory', 'leadership',
    'passion', 'spiritual', 'soul', 'loss', 'grief', 'language', 'psychology', 'friends', 'paranormal-romance',
    'learning', 'imagination', 'world', 'magic', 'sadness', 'feminism', 'depression']


class GoodreadsSource(IQuoteSource):
    def __init__(self):
        super(IQuoteSource, self).__init__()

    @classmethod
    def get_info(cls):
        return {
            "name": "Goodreads",
            "description": _("Fetches quotes from Goodreads.com"),
            "author": "Peter Levi",
            "version": "0.1"
        }

    def supports_search(self):
        return True

    def get_random(self):
        return self.get_for_keyword(random.choice(KEYWORDS))[:4]

    def get_for_author(self, author):
        logger.info(lambda: "Fetching quotes from Goodreads for author=%s" % author)

        url = iri2uri("https://www.goodreads.com/quotes/search?utf8=\u2713&q=%s" % author)
        soup = Util.html_soup(url)
        page_links = list(Util.safe_map(int,
                                        [pagelink.contents[0] for pagelink in
                                         soup.find_all(href=re.compile('quotes/search.*page='))]))
        if page_links:
            page = random.randint(1, max(page_links))
            url = iri2uri("https://www.goodreads.com/quotes/search?utf8=\u2713&q=%s&page=%d" % (author, page))
            soup = Util.html_soup(url)

        return self.get_from_soup(url, soup)

    def get_for_keyword(self, keyword):
        logger.info(lambda: "Fetching quotes from Goodreads for keyword=%s" % keyword)

        url = iri2uri("https://www.goodreads.com/quotes/tag?utf8=\u2713&id=%s" % keyword)
        soup = Util.html_soup(url)
        page_links = list(Util.safe_map(int,
                                        [pagelink.contents[0] for pagelink in
                                         soup.find_all(href=re.compile('quotes/tag.*page='))]))
        if page_links:
            page = random.randint(1, max(page_links))
            url = iri2uri("https://www.goodreads.com/quotes/tag?utf8=\u2713&id=%s&page=%d" % (keyword, page))
            soup = Util.html_soup(url)

        return self.get_from_soup(url, soup)

    def get_from_soup(self, url, soup):
        logger.info(lambda: "Used Goodreads url %s" % url)
        quotes = []

        for div in soup.find_all('div', 'quoteText'):
            logger.debug(lambda: "Parsing quote for div\n%s" % div)
            try:
                quote_text = "\n".join(div.find_all(text=True, recursive=False)).replace('―', '').strip()
                author = div.find("span", attrs={"class": "authorOrTitle"}).string.strip().strip(',')
                first_a = div.find('a')
                if first_a:
                    link = "https://www.goodreads.com" + div.find('a')["href"]
                else:
                    link = None  # No link given
                quotes.append({"quote": quote_text, "author": author, "sourceName": "Goodreads", "link": link})
            except Exception:
                logger.exception(lambda: "Could not extract Goodreads quote")

        if not quotes:
            logger.warning(lambda: "Goodreads: no quotes found at %s" % url)

        return quotes
