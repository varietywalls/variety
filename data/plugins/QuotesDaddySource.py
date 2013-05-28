from variety.Util import Util
from variety.plugins.IQuoteSource import IQuoteSource

import logging
logger = logging.getLogger("variety")

class QuotesDaddySource(IQuoteSource):
    @classmethod
    def get_info(cls):
        raise Exception
        return {
            "name": "QuotesDaddy quotes"
        }

    def supports_keywords(self):
        return False

    def get_quote(self, keywords=None):
        url = "http://www.quotesdaddy.com/feed"
        try:
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

            return {"quote": quote, "author": author, "sourceName": "QuotesDaddy", "link": link}
        except Exception:
            logger.exception("Could not fetch or extract quote")
            return None
