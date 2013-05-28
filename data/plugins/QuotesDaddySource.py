from bs4 import BeautifulSoup
from variety.Util import Util
from variety.plugins.IQuoteSource import IQuoteSource

import logging
logger = logging.getLogger("variety")

class QuotesDaddySource(IQuoteSource):
    @classmethod
    def get_info(cls):
        return {
            "name": "QuotesDaddy quotes"
        }

    def supports_keywords(self):
        return False

    def get_quote(self, keywords=None):
        url = "http://www.quotesdaddy.com/feed"
        try:
            quote = QuotesDaddySource.extract_quote(Util.fetch(url))
            if not quote:
                logger.warning("Could not find quotes for URL " + url)
            return quote
        except Exception:
            logger.exception("Could not fetch or extract quote")
        return None

    @staticmethod
    def extract_quote(xml):
        bs = BeautifulSoup(xml, "xml")
        item = bs.find("item")
        if not item:
            return None
        link = item.find("link").contents[0].strip()
        s = item.find("description").contents[0]
        author = s[s.rindex('- ') + 1:].strip()
        quote = s[:s.rindex('- ')].strip().replace('"', '').replace('<br>', '\n').replace('<br/>', '\n').strip()
        quote = u"\u201C%s\u201D" % quote
        return {"quote": quote, "author": author, "sourceName": "QuotesDaddy", "link": link}


#    @staticmethod
#    def choose_random_feed_url(options, skip_urls=set()):
#        urls = []
#        tags = options.quotes_tags.split(",")
#        for tag in tags:
#            if tag.strip():
#                url = "http://www.quotesdaddy.com/feed/tagged/" + urllib.quote_plus(tag.strip())
#                if not url in skip_urls:
#                    urls.append(url)
#
#        authors = options.quotes_authors.split(",")
#        for author in authors:
#            if author.strip():
#                url = "http://www.quotesdaddy.com/feed/author/" + urllib.quote_plus(author.strip())
#                if not url in skip_urls:
#                    urls.append(url)
#
#        if not urls:
#            urls.append("http://www.quotesdaddy.com/feed")
#
#        return random.choice(urls)

