from variety.Util import Util
from variety.plugit.IQuoteSource import IQuoteSource

class DummyQuoteSource(IQuoteSource):
    def get_quote(self):
        return {"quote": "Dummy quote " + Util.random_hash(), "author": "Dummy author " + Util.random_hash(), "link": None}
