from variety.Util import Util
from variety.plugins.IQuoteSource import IQuoteSource

class DummyQuoteSource(IQuoteSource):
    @classmethod
    def get_info(cls):
        return {
            "name": "Dummy Quote Source"
        }

    def supports_keywords(self):
        return True

    def get_quote(self, keywords=None):
        return {"quote": "Dummy quote " + Util.random_hash(),
                "author": "Dummy author " + Util.random_hash()}
