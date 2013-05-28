from jumble.IPlugin import IPlugin

class IQuoteSource(IPlugin):
    def supports_keywords(self):
        return False

    def get_quote(self, keywords=None):
        """Return some quote"""
        return {
            "quote": "Quote",
            "author": "Author",
            "sourceName": "My Quote Site",
            "link": "http://example.com"
        }
