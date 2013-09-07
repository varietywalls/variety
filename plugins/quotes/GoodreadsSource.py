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
            "name": "Quotes from Goodreads",
            "description": "Fetches quotes from Goodreads.com",
            "author": "Peter Levi",
            "version": "0.1"
        }

    def supports_search(self):
        return True

    def get_random(self):
        return self.get_for_keyword(random.choice(KEYWORDS))

    def get_for_author(self, author):
        return self.get_for_keyword(author)

    def get_for_keyword(self, keyword):
        logger.info("Fetching quotes from Goodreads for keyword=%s" % keyword)

        quotes = []

        url = iri2uri(u"http://www.goodreads.com/quotes/search?utf8=\u2713&q=%s" % keyword)
        soup = Util.html_soup(url)
        page_links = list(Util.safe_map(int,
            [pagelink.contents[0] for pagelink in soup.find_all(href=re.compile('quotes/search.*page='))]))
        if page_links:
            page = random.randint(1, max(page_links))
            url = iri2uri(u"http://www.goodreads.com/quotes/search?utf8=\u2713&q=%s&page=%d" % (keyword, page))
            soup = Util.html_soup(url)

        logger.info("Used Goodreads url %s" % url)
        for div in soup.find_all('div', 'quoteText'):
            logger.debug("Parsing quote for div\n%s" % div)
            try:
                quote_text = u""
                first_a = div.find('a')
                for elem in div.contents:
                    if elem == first_a:
                        break
                    else:
                        quote_text += unicode(elem)
                quote_text = quote_text.replace(u'<br>', '\n').replace(u'<br/>', '\n').replace(u'―', '').strip()

                author = first_a.contents[0]
                link = "http://www.goodreads.com" + div.find('a')["href"]
                if div.find('i'):
                    author = author + ', ' + div.find('i').find('a').contents[0]
                quotes.append({"quote": quote_text, "author": author, "sourceName": "Goodreads", "link": link})
            except Exception:
                logger.exception("Could not extract Goodreads quote")

        return quotes
