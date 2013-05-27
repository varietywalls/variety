from IPlugin import IPlugin

class IQuoteSource(IPlugin):
    def get_quote(self):
        """Return some random quote"""
        return {
            "quote": "Quote",
            "author": "Author",
            "sourceName": "My Quote Site",
            "link": "http://example.com"
        }
