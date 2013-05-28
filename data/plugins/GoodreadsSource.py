import random
import re
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

# TODO cache all quotes from a page, keyed by keyword to reduce bandwidth usage
class GoodreadsSource(IQuoteSource):
    @classmethod
    def get_info(cls):
        return {
            "name": "Goodreads quotes"
        }

    def supports_keywords(self):
        return True

    def get_quote(self, keywords=None):
        keyword = random.choice(keywords or KEYWORDS)
        url = "http://www.goodreads.com/quotes/search?q=%s" % keyword
        try:
            soup = Util.html_soup(url)
            page_links = Util.safe_map(int,
                [pagelink.contents[0] for pagelink in soup.find_all(href=re.compile('quotes/search.*page='))])
            if page_links:
                page = random.randint(1, max(page_links))
                url = "http://www.goodreads.com/quotes/search?q=%s&page=%d" % (keyword, page)
                soup = Util.html_soup(url)
            print url
            div = random.choice(soup.find_all('div', 'quoteText'))
            quote = div.contents[0].strip()
            author = div.find('a').contents[0]
            link = "http://www.goodreads.com" + div.find('a')["href"]
            if div.find('i'):
                author = author + ', ' + div.find('i').find('a').contents[0]

            print str({"quote": quote, "author": author, "sourceName": "Goodreads", "link": link})
            return {"quote": quote, "author": author, "sourceName": "Goodreads", "link": link}
        except Exception:
            logger.exception("Could not fetch or extract quote")
            return None
