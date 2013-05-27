from IPlugin import IPlugin

class IQuotePlugin(IPlugin):
    def get_quote(self):
        return ("Quote", "Author")
