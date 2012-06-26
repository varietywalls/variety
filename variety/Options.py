import os
from configobj import ConfigObj

import logging
logger = logging.getLogger('variety')

class Options:
    class SourceType:
        IMAGE = 1
        FOLDER = 2
        WN = 3
        type_to_str = {IMAGE: "image", FOLDER: "folder", WN: "wn"}
        str_to_type = {"image": IMAGE, "folder": FOLDER, "wn": WN}

    def __init__(self):
        self.configfile = os.path.expanduser("~/.variety/variety.conf")

    def read(self):
        self.use_defaults()

        try:
            config = ConfigObj(self.configfile)

            try:
                self.change_interval = int(config["change_interval"])
                if self.change_interval < 5:
                    self.change_interval = 5
            except Exception:
                pass

            try:
                self.change_on_start = config["change_on_start"].lower() in ["enabled", "1", "true", "on", "yes"]
            except Exception:
                pass

            try:
                self.download_interval = int(config["download_interval"])
                if self.download_interval < 30:
                    self.download_interval = 30
            except Exception:
                pass

            try:
                self.desired_color = map(int, config["desired_color"].split())
            except Exception:
                self.desired_color = None

            try:
                self.favorites_folder = config["favorites_folder"]
            except Exception:
                pass

            if "sources" in config:
                self.sources = []
                sources = config["sources"]
                for v in sources.values():
                    try:
                        s = v.strip().split('|')
                        enabled = s[0].lower() in ["enabled", "1", "true", "on", "yes"]
                        self.sources.append((enabled, (self.str_to_type(s[1])), s[2]))
                    except Exception:
                        logger.exception("Cannot parse source: " + v)

            if "filters" in config:
                self.filters = []
                filters = config["filters"]
                for v in filters.values():
                    try:
                        s = v.strip().split('|')
                        enabled = s[0].lower() in ["enabled", "1", "true", "on", "yes"]
                        self.filters.append((enabled, s[1], s[2]))
                    except Exception:
                        logger.exception("Cannot parse filter: " + v)

        except Exception:
            logger.exception("Could not read configuration:")

    def str_to_type(self, s):
        s = s.lower()
        if s in Options.SourceType.str_to_type:
            return Options.SourceType.str_to_type[s]
        else:
            raise Exception("Unknown source type")

    def type_to_str(self, stype):
        return Options.SourceType.type_to_str[stype]

    def use_defaults(self):
        self.change_on_start = False
        self.change_interval = 60
        self.download_interval = 60
        self.desired_color = None
        self.favorites_folder = os.path.expanduser("~/.variety/Favorites")

        self.sources = [
            (True, Options.SourceType.FOLDER, "/usr/share/backgrounds/"),
            (True, Options.SourceType.WN, "http://wallpapers.net/nature-desktop-wallpapers.html"),
            (True, Options.SourceType.WN, "http://wallpapers.net/top_wallpapers.html")
        ]

        self.filters = [
            (False, "Grayscale", "-type Grayscale"),
            (False, "Oil Painting", "-paint 6"),
            (False, "Charcoal Painting", "-charcoal 3")
        ]

    def write(self):
        try:
            config = ConfigObj(self.configfile)
        except Exception:
            config = ConfigObj()
            config.filename = self.configfile

        try:
            config["change_interval"] = str(self.change_interval)
            config["download_interval"] = str(self.download_interval)
            config["desired_color"] = " ".join(map(str, self.desired_color)) if self.desired_color else "None"

            config["sources"] = {}
            for i, s in enumerate(self.sources):
                config["sources"]["src" + str(i+1)] = str(s[0]) + "|" + str(self.type_to_str(s[1])) + "|" + s[2]

            config.write()

        except Exception:
            logger.exception("Could not write configuration:")


if __name__ == "__main__":
    formatter = logging.Formatter("%(levelname)s:%(name)s: %(funcName)s() '%(message)s'")

    logger = logging.getLogger('variety')
    logger_sh = logging.StreamHandler()
    logger_sh.setFormatter(formatter)
    logger.addHandler(logger_sh)

    o = Options()
    o.read()
    print o.sources
    print o.filters
    o.write()
