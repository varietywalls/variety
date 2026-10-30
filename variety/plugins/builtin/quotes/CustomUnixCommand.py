import subprocess
import getpass as gt
from locale import gettext as _

from variety.Options import Options
from variety.plugins.IQuoteSource import IQuoteSource


class CliSource(IQuoteSource):
    @classmethod
    def get_info(cls):
        return {
            "name": "Custom Unix Command",
            "description": _(
                "Display output of UNIX commands over your wallpaper. "
                "You may want to install additional "
                "tools like gcalcli, Khal or cal."
            ),
            "author": "Paul Portocarrero",
            "version": "0.1",
        }

    def __init__(self):
        super().__init__()
        self.user_name = gt.getuser()
        self.options = Options()
        self.options.read()
        # print(self.options.quotes_unix_cmd)
        try:
            self.cmd = (self.options.quotes_unix_cmd).split(" ")
        except:
            self.cmd = ["cal"]

    def needs_internet(self):
        return False

    def get_random(self):
        std_output = subprocess.check_output(self.cmd).decode()

        return [
            {
                "quote": std_output,
                "author": f"{self.user_name}:~$ {self.cmd[0]}",
                "sourceName": "Custom Unix Command",
                "link": None,
            }
        ]
