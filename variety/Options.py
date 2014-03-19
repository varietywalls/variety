# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (c) 2012, Peter Levi <peterlevi@peterlevi.com>
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
import hashlib
from configobj import ConfigObj
from configobj import DuplicateError
from variety.Util import Util
from variety_lib import varietyconfig

import logging

logger = logging.getLogger('variety')

TRUTH_VALUES = ["enabled", "1", "true", "on", "yes"]

class Options:
    OUTDATED_HASHES = {'clock_filter': ['dca6bd2dfa2b8c4e2db8801e39208f7f']}

    class SourceType:
        IMAGE = 1
        FOLDER = 2
        FAVORITES = 3
        FETCHED = 4
        WN = 5
        DESKTOPPR = 6
        FLICKR = 7
        APOD = 8
        WALLBASE = 9
        MEDIA_RSS = 10
        EARTH = 11
        RECOMMENDED = 12

        type_to_str = {
            FAVORITES: "favorites",
            FETCHED: "fetched",
            IMAGE: "image",
            FOLDER: "folder",
            WN: "wn",
            DESKTOPPR: "desktoppr",
            FLICKR: "flickr",
            APOD: "apod",
            WALLBASE: "wallbase",
            MEDIA_RSS: "mediarss",
            EARTH: "earth",
            RECOMMENDED: "recommended"
        }

        str_to_type = dict((v,k) for k, v in type_to_str.items())

        dl_types = [WN, DESKTOPPR, FLICKR, APOD, WALLBASE, MEDIA_RSS, EARTH, RECOMMENDED]

    class LightnessMode:
        DARK = 0
        LIGHT = 1

    def __init__(self):
        self.configfile = os.path.expanduser("~/.config/variety/variety.conf")

    def read(self):
        self.set_defaults()

        try:
            config = self.read_config()
            needs_writing = self.fix_outdated(config)

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
                self.quota_enabled = config["quota_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.quota_size = int(config["quota_size"])
                if self.quota_size < 50:
                    self.quota_size = 50
            except Exception:
                pass

            try:
                self.favorites_folder = os.path.expanduser(config["favorites_folder"])
            except Exception:
                pass

            try:
                favorites_ops_text = config["favorites_operations"]
                self.favorites_operations = list([x.strip().split(':') for x in favorites_ops_text.split(';') if x])
            except Exception:
                pass

            try:
                self.fetched_folder = os.path.expanduser(config["fetched_folder"])
            except Exception:
                pass

            try:
                self.clipboard_enabled = config["clipboard_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.clipboard_use_whitelist = config["clipboard_use_whitelist"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.clipboard_hosts = config["clipboard_hosts"].lower().split(',')
            except Exception:
                pass

            try:
                icon = config["icon"]
                if icon in ["Light", "Dark", "Current", "None"] or (os.access(icon, os.R_OK) and Util.is_image(icon)):
                    self.icon = icon
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

            try:
                self.min_size_enabled = config["min_size_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.min_size = int(config["min_size"])
                self.min_size = max(0, min(100, self.min_size))
            except Exception:
                pass

            try:
                self.use_landscape_enabled = config["use_landscape_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.lightness_enabled = config["lightness_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.lightness_mode = int(config["lightness_mode"])
                self.lightness_mode = max(0, min(1, self.lightness_mode))
            except Exception:
                pass

            try:
                self.min_rating_enabled = config["min_rating_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.min_rating = int(config["min_rating"])
                self.min_rating = max(1, min(5, self.min_rating))
            except Exception:
                pass

            try:
                self.show_rating_enabled = config["show_rating_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.smart_enabled = config["smart_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.smart_notice_shown = config["smart_notice_shown"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.facebook_enabled = config["facebook_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.facebook_show_dialog = config["facebook_show_dialog"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.facebook_message = config["facebook_message"].strip()
            except Exception:
                pass

            try:
                self.copyto_enabled = config["copyto_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.copyto_folder = os.path.expanduser(config["copyto_folder"])
            except Exception:
                pass

            try:
                self.clock_enabled = config["clock_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.clock_filter = config["clock_filter"].strip()
            except Exception:
                pass

            try:
                self.clock_font = config["clock_font"]
            except Exception:
                pass

            try:
                self.clock_date_font = config["clock_date_font"]
            except Exception:
                pass

            try:
                self.quotes_enabled = config["quotes_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.quotes_font = config["quotes_font"]
            except Exception:
                pass

            try:
                self.quotes_text_color = map(int, config["quotes_text_color"].split())
                for i, x in enumerate(self.quotes_text_color):
                    self.quotes_text_color[i] = max(0, min(255, x))
            except Exception:
                pass

            try:
                self.quotes_bg_color = map(int, config["quotes_bg_color"].split())
                for i, x in enumerate(self.quotes_bg_color):
                    self.quotes_bg_color[i] = max(0, min(255, x))
            except Exception:
                pass

            try:
                self.quotes_bg_opacity = int(float(config["quotes_bg_opacity"]))
                self.quotes_bg_opacity = max(0, min(100, self.quotes_bg_opacity))
            except Exception:
                pass

            try:
                self.quotes_text_shadow = config["quotes_text_shadow"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.quotes_text_color = map(int, config["quotes_text_color"].split())
                for i, x in enumerate(self.quotes_text_color):
                    self.quotes_text_color[i] = max(0, min(255, x))
            except Exception:
                pass

            try:
                self.quotes_disabled_sources = config["quotes_disabled_sources"].strip().split('|')
            except Exception:
                pass

            try:
                self.quotes_tags = config["quotes_tags"]
            except Exception:
                pass

            try:
                self.quotes_authors = config["quotes_authors"]
            except Exception:
                pass

            try:
                self.quotes_change_enabled = config["quotes_change_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.quotes_change_interval = int(config["quotes_change_interval"])
                if self.quotes_change_interval < 10:
                    self.quotes_change_interval = 10
            except Exception:
                pass

            try:
                self.quotes_width = int(float(config["quotes_width"]))
                self.quotes_width = max(0, min(100, self.quotes_width))
            except Exception:
                pass

            try:
                self.quotes_hpos = int(float(config["quotes_hpos"]))
                self.quotes_hpos = max(0, min(100, self.quotes_hpos))
            except Exception:
                pass

            try:
                self.quotes_vpos = int(float(config["quotes_vpos"]))
                self.quotes_vpos = max(0, min(100, self.quotes_vpos))
            except Exception:
                pass

            try:
                self.quotes_favorites_file = os.path.expanduser(config["quotes_favorites_file"])
            except Exception:
                pass

            if "sources" in config:
                self.sources = []
                sources = config["sources"]
                for v in sources.values():
                    try:
                        self.sources.append(Options.parse_source(v))
                    except Exception:
                        logger.exception("Cannot parse source: " + v)

            self.parse_autosources()

            for s in self.sources:
                if s[1] == Options.SourceType.RECOMMENDED and not self.smart_enabled:
                    s[0] = False

            if "filters" in config:
                self.filters = []
                filters = config["filters"]
                for v in filters.values():
                    try:
                        self.filters.append(Options.parse_filter(v))
                    except Exception:
                        logger.exception("Cannot parse filter: " + str(v))

            self.parse_autofilters()

            if needs_writing:
                logger.info("Some outdated settings were updated, writing the changes")
                self.write()

        except Exception:
            logger.exception("Could not read configuration:")

    def fix_outdated(self, config):
        changed = False
        for key, outdated_hashes in Options.OUTDATED_HASHES.items():
            if key in config:
                current_hash = hashlib.md5(config[key]).hexdigest()
                if current_hash in outdated_hashes:
                    # entry is outdated: delete it and use the default
                    logger.warning("Option " + key + " has an outdated value, using the new default")
                    changed = True
                    del config[key]
        return changed

    def parse_autosources(self):
        try:
            with open(varietyconfig.get_data_file("config", "sources.txt")) as f:
                for line in f:
                    if not line.strip() or line.strip().startswith('#'):
                        continue
                    try:
                        s = Options.parse_source(line.strip())
                        if s[1] in [src[1] for src in self.sources]:
                            continue
                        self.sources.append(s)
                    except Exception:
                        logger.exception("Cannot parse source in sources.txt: " + line)
        except Exception:
            logger.exception("Cannot open sources.txt")

    def parse_autofilters(self):
        try:
            with open(varietyconfig.get_data_file("config", "filters.txt")) as f:
                for line in f:
                    if not line.strip() or line.strip().startswith('#'):
                        continue
                    try:
                        s = Options.parse_filter(line.strip())
                        if not s[1].lower() in [f[1].lower() for f in self.filters]:
                            self.filters.append(s)
                    except Exception:
                        logger.exception("Cannot parse filter in filters.txt: " + line)
        except Exception:
            logger.exception("Cannot open filters.txt")

    @staticmethod
    def parse_source(v):
        s = v.strip().split('|')
        enabled = s[0].lower() in TRUTH_VALUES
        return [enabled, (Options.str_to_type(s[1])), s[2]]

    @staticmethod
    def parse_filter(v):
        s = v.strip().split('|')
        enabled = s[0].lower() in TRUTH_VALUES
        return [enabled, s[1], s[2]]

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

        self.download_enabled = True
        self.download_interval = 600
        self.download_folder = os.path.expanduser("~/.config/variety/Downloaded")
        self.quota_enabled = True
        self.quota_size = 500

        self.favorites_folder = os.path.expanduser("~/.config/variety/Favorites")
        self.favorites_operations = [["Downloaded", "Copy"], ["Fetched", "Move"], ["Others", "Copy"]]

        self.fetched_folder = os.path.expanduser("~/.config/variety/Fetched")
        self.clipboard_enabled = False
        self.clipboard_use_whitelist = True
        self.clipboard_hosts = "wallbase.cc,ns223506.ovh.net,wallpapers.net,flickr.com,imgur.com,deviantart.com,interfacelift.com,vladstudio.com".split(',')

        self.icon = "Light"

        self.desired_color_enabled = False
        self.desired_color = None
        self.min_size_enabled = False
        self.min_size = 80
        self.use_landscape_enabled = True
        self.lightness_enabled = False
        self.lightness_mode = Options.LightnessMode.DARK
        self.min_rating_enabled = False
        self.min_rating = 4
        self.show_rating_enabled = False

        self.smart_enabled = False
        self.smart_notice_shown = False
        self.facebook_enabled = True
        self.facebook_show_dialog = True
        self.facebook_message = ""

        self.copyto_enabled = False
        self.copyto_folder = "Default"

        self.clock_enabled = False
        self.clock_font = "Ubuntu Condensed, 70"
        self.clock_date_font = "Ubuntu Condensed, 30"
        self.clock_filter = "-density 100 -font `fc-match -f '%{file[0]}' '%CLOCK_FONT_NAME'` -pointsize %CLOCK_FONT_SIZE -gravity SouthEast -fill '#00000044' -annotate 0x0+[%HOFFSET+58]+[%VOFFSET+108] '%H:%M' -fill white -annotate 0x0+[%HOFFSET+60]+[%VOFFSET+110] '%H:%M' -font `fc-match -f '%{file[0]}' '%DATE_FONT_NAME'` -pointsize %DATE_FONT_SIZE -fill '#00000044' -annotate 0x0+[%HOFFSET+58]+[%VOFFSET+58] '%A, %B %d' -fill white -annotate 0x0+[%HOFFSET+60]+[%VOFFSET+60] '%A, %B %d'"

        self.quotes_enabled = False
        self.quotes_font = "Bitstream Charter 30"
        self.quotes_text_color = (255, 255, 255)
        self.quotes_bg_color = (80, 80, 80)
        self.quotes_bg_opacity = 55
        self.quotes_text_shadow = False
        self.quotes_disabled_sources = []
        self.quotes_tags = ""
        self.quotes_authors = ""
        self.quotes_change_enabled = False
        self.quotes_change_interval = 300
        self.quotes_width = 70
        self.quotes_hpos = 100
        self.quotes_vpos = 40
        self.quotes_favorites_file = os.path.expanduser("~/.config/variety/favorite_quotes.txt")


        self.sources = [
            [True, Options.SourceType.FAVORITES, "The Favorites folder"],
            [True, Options.SourceType.FETCHED, "The Fetched folder"],
            [True, Options.SourceType.FOLDER, "/usr/share/backgrounds/"],
            [True, Options.SourceType.DESKTOPPR, "Random wallpapers from Desktoppr.co"],
            [False, Options.SourceType.APOD, "NASA's Astronomy Picture of the Day"],
            [True, Options.SourceType.WN, "http://wallpapers.net/nature-desktop-wallpapers.html"],
            [True, Options.SourceType.FLICKR, "user:www.flickr.com/photos/peter-levi/;user_id:93647178@N00;"],
            [True, Options.SourceType.WALLBASE, "autumn"]
        ]

        self.filters = [
            [False, "Keep original", ""],
            [False, "Grayscale", "-type Grayscale"],
            [False, "Heavy blur", "-blur 120x40"],
            [False, "Oil painting", "-paint 6"],
            [False, "Charcoal painting", "-charcoal 3"],
            [False, "Pencil sketch", """-colorspace gray \( +clone -tile ~/.config/variety/pencil_tile.png -draw "color 0,0 reset" +clone +swap -compose color_dodge -composite \) -fx 'u*.2+v*.8'"""],
            [False, "Pointilism", "-spread 10 -noise 3"],
            [False, "Pixellate", "-scale 3% -scale 3333%"]
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
            config["download_folder"] = Util.collapseuser(self.download_folder)

            config["quota_enabled"] = str(self.quota_enabled)
            config["quota_size"] = str(self.quota_size)

            config["favorites_folder"] = Util.collapseuser(self.favorites_folder)
            config["favorites_operations"] = ';'.join(':'.join(x) for x in self.favorites_operations)

            config["fetched_folder"] = Util.collapseuser(self.fetched_folder)
            config["clipboard_enabled"] = self.clipboard_enabled
            config["clipboard_use_whitelist"] = self.clipboard_use_whitelist
            config["clipboard_hosts"] = ','.join(self.clipboard_hosts)

            config["icon"] = self.icon

            config["desired_color_enabled"] = str(self.desired_color_enabled)
            config["desired_color"] = " ".join(map(str, self.desired_color)) if self.desired_color else "None"
            config["min_size_enabled"] = str(self.min_size_enabled)
            config["min_size"] = str(self.min_size)
            config["use_landscape_enabled"] = str(self.use_landscape_enabled)
            config["lightness_enabled"] = str(self.lightness_enabled)
            config["lightness_mode"] = str(self.lightness_mode)
            config["min_rating_enabled"] = str(self.min_rating_enabled)
            config["min_rating"] = str(self.min_rating)
            config["show_rating_enabled"] = str(self.show_rating_enabled)

            config["smart_enabled"] = str(self.smart_enabled)
            config["smart_notice_shown"] = str(self.smart_notice_shown)

            config["facebook_enabled"] = str(self.facebook_enabled)
            config["facebook_show_dialog"] = str(self.facebook_show_dialog)
            config["facebook_message"] = str(self.facebook_message)

            config["copyto_enabled"] = str(self.copyto_enabled)
            config["copyto_folder"] = Util.collapseuser(str(self.copyto_folder))

            config["clock_enabled"] = str(self.clock_enabled)
            config["clock_filter"] = str(self.clock_filter)
            config["clock_font"] = str(self.clock_font)
            config["clock_date_font"] = str(self.clock_date_font)

            config["quotes_enabled"] = str(self.quotes_enabled)
            config["quotes_font"] = str(self.quotes_font)
            config["quotes_text_color"] = " ".join(map(str, self.quotes_text_color))
            config["quotes_bg_color"] = " ".join(map(str, self.quotes_bg_color))
            config["quotes_bg_opacity"] = str(self.quotes_bg_opacity)
            config["quotes_text_shadow"] = str(self.quotes_text_shadow)
            config["quotes_disabled_sources"] = '|'.join(self.quotes_disabled_sources)
            config["quotes_tags"] = str(self.quotes_tags)
            config["quotes_authors"] = str(self.quotes_authors)
            config["quotes_change_enabled"] = str(self.quotes_change_enabled)
            config["quotes_change_interval"] = str(self.quotes_change_interval)
            config["quotes_width"] = str(self.quotes_width)
            config["quotes_hpos"] = str(self.quotes_hpos)
            config["quotes_vpos"] = str(self.quotes_vpos)
            config["quotes_favorites_file"] = Util.collapseuser(self.quotes_favorites_file)

            config["sources"] = {}
            for i, s in enumerate(self.sources):
                config["sources"]["src" + str(i + 1)] = str(s[0]) + "|" + str(Options.type_to_str(s[1])) + "|" + s[2]

            config["filters"] = {}
            for i, f in enumerate(self.filters):
                config["filters"]["filter" + str(i + 1)] = str(f[0]) + "|" + f[1] + "|" + f[2]

            config.write()

        except Exception:
            logger.exception("Could not write configuration:")

    @staticmethod
    def set_options(opts):
        config = Options().read_config()
        for key, value in opts:
            config[key] = value
        config.write()

    def read_config(self):
        config = ConfigObj(raise_errors=False)
        config.filename = self.configfile
        try:
            config.reload()
        except DuplicateError:
            logger.warning("Duplicate keys in config file, please fix this")
        return config

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
