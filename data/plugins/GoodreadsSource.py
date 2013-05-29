# coding=utf-8
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
        self.cache = {}

    @classmethod
    def get_info(cls):
        return {
            "name": "Quotes from Goodreads",
            "description": "Fetches quotes from Goodreads.com",
            "author": "Peter Levi",
            "version": "0.1"
        }

    def supports_keywords(self):
        return True

    def get_quote(self, keywords=None):
        keyword = random.choice(keywords or KEYWORDS)
        logger.info("Fetching quotes from Goodreads for keyword=%s" % keyword)

        if not keyword in self.cache:
            url = iri2uri(u"http://www.goodreads.com/quotes/search?utf8=\u2713&q=%s".encode("utf-8") % keyword)
            soup = Util.html_soup(url)
            page_links = list(Util.safe_map(int,
                [pagelink.contents[0] for pagelink in soup.find_all(href=re.compile('quotes/search.*page='))]))
            if page_links:
                page = random.randint(1, max(page_links))
                url = iri2uri(u"http://www.goodreads.com/quotes/search?utf8=\u2713&q=%s&page=%d".encode("utf-8") % (keyword, page))
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
                    self.cache.setdefault(keyword, {})[quote_text] = \
                        {"quote": quote_text, "author": author, "sourceName": "Goodreads", "link": link}
                except Exception:
                    logger.exception("Could not extract Goodreads quote")

        quote = random.choice(self.cache[keyword].values())
        del self.cache[keyword][quote["quote"]]
        if not self.cache[keyword]:
            del self.cache[keyword]

        return quote
