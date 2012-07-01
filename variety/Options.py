#!/usr/bin/python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2012 Peter Levi <peterlevi@peterlevi.com>
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import os
from configobj import ConfigObj

import logging

logger = logging.getLogger('variety')

TRUTH_VALUES = ["enabled", "1", "true", "on", "yes"]

class Options:
    class SourceType:
        IMAGE = 1
        FOLDER = 2
        FAVORITES = 3
        WN = 4
        DESKTOPPR = 5

        type_to_str = {IMAGE: "image", FOLDER: "folder", WN: "wn", FAVORITES: "fav", DESKTOPPR: "desktoppr"}
        str_to_type = {"image": IMAGE, "folder": FOLDER, "wn": WN, "fav": FAVORITES, "desktoppr": DESKTOPPR}

    def __init__(self):
        self.configfile = os.path.expanduser("~/.config/variety/variety.conf")

    def read(self):
        self.set_defaults()

        try:
            config = ConfigObj(self.configfile)

            try:
                self.change_enabled = config["change_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.change_on_start = config["change_on_start"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.change_interval = int(config["change_interval"])
                if self.change_interval < 5:
                    self.change_interval = 5
            except Exception:
                pass

            try:
                self.download_enabled = config["download_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.download_interval = int(config["download_interval"])
                if self.download_interval < 60:
                    self.download_interval = 60
            except Exception:
                pass

            try:
                self.download_folder = os.path.expanduser(config["download_folder"])
            except Exception:
                pass

            try:
                self.favorites_folder = os.path.expanduser(config["favorites_folder"])
            except Exception:
                pass

            try:
                self.desired_color_enabled = config["desired_color_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.desired_color = map(int, config["desired_color"].split())
                for i, x in enumerate(self.desired_color):
                    self.desired_color[i] = max(0, min(255, x))
            except Exception:
                self.desired_color = None

            if "sources" in config:
                self.sources = []
                sources = config["sources"]
                for v in sources.values():
                    try:
                        s = v.strip().split('|')
                        enabled = s[0].lower() in TRUTH_VALUES
                        self.sources.append([enabled, (Options.str_to_type(s[1])), s[2]])
                    except Exception:
                        logger.exception("Cannot parse source: " + v)

            if "filters" in config:
                self.filters = []
                filters = config["filters"]
                for v in filters.values():
                    try:
                        s = v.strip().split('|')
                        enabled = s[0].lower() in TRUTH_VALUES
                        self.filters.append([enabled, s[1], s[2]])
                    except Exception:
                        logger.exception("Cannot parse filter: " + v)

        except Exception:
            logger.exception("Could not read configuration:")

    @staticmethod
    def str_to_type(s):
        s = s.lower()
        if s in Options.SourceType.str_to_type:
            return Options.SourceType.str_to_type[s]
        else:
            raise Exception("Unknown source type")

    @staticmethod
    def type_to_str(stype):
        return Options.SourceType.type_to_str[stype]

    def set_defaults(self):
        self.change_enabled = True
        self.change_on_start = False
        self.change_interval = 300
        self.desired_color_enabled = False
        self.desired_color = None
        self.download_enabled = True
        self.download_interval = 600
        self.download_folder = os.path.expanduser("~/.config/variety/Downloaded")
        self.favorites_folder = os.path.expanduser("~/.config/variety/Favorites")

        self.sources = [
            [True, Options.SourceType.FAVORITES, "The Favorites folder"],
            [True, Options.SourceType.FOLDER, "/usr/share/backgrounds/"],
            [True, Options.SourceType.DESKTOPPR, "Random wallpapers from Desktoppr.co"],
            [True, Options.SourceType.WN, "http://wallpapers.net/nature-desktop-wallpapers.html"],
            [True, Options.SourceType.WN, "http://wallpapers.net/top_wallpapers.html"]
        ]

        self.filters = [
            [False, "Grayscale", "-type Grayscale"],
            [False, "Heavy blur", "-blur 70x70"],
            [False, "Oil painting", "-paint 6"],
            [False, "Charcoal painting", "-charcoal 3"],
            [False, "Pointilism", "-spread 10 -noise 3"]
        ]

    def write(self):
        try:
            config = ConfigObj(self.configfile)
        except Exception:
            config = ConfigObj()
            config.filename = self.configfile

        try:
            config["change_enabled"] = str(self.change_enabled)
            config["change_on_start"] = str(self.change_on_start)
            config["change_interval"] = str(self.change_interval)

            config["download_enabled"] = str(self.download_enabled)
            config["download_interval"] = str(self.download_interval)
            config["download_folder"] = self.download_folder

            config["favorites_folder"] = self.favorites_folder

            config["desired_color_enabled"] = str(self.desired_color_enabled)
            config["desired_color"] = " ".join(map(str, self.desired_color)) if self.desired_color else "None"

            config["sources"] = {}
            for i, s in enumerate(self.sources):
                config["sources"]["src" + str(i + 1)] = str(s[0]) + "|" + str(Options.type_to_str(s[1])) + "|" + s[2]

            config["filters"] = {}
            for i, f in enumerate(self.filters):
                config["filters"]["filter" + str(i + 1)] = str(f[0]) + "|" + f[1] + "|" + f[2]

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
