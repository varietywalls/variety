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
import hashlib
import logging
import os

from configobj import ConfigObj, DuplicateError

from variety.profile import get_profile_path
from variety.Util import Util
from variety_lib import varietyconfig

logger = logging.getLogger("variety")

TRUTH_VALUES = ["enabled", "1", "true", "on", "yes"]


class Options:
    OUTDATED_HASHES = {"clock_filter": ["dca6bd2dfa2b8c4e2db8801e39208f7f"]}
    SIMPLE_DOWNLOADERS = []  # set by VarietyWindow at start
    IMAGE_SOURCES = []  # set by VarietyWindow at start
    CONFIGURABLE_IMAGE_SOURCES = []  # set by VarietyWindow at start
    CONFIGURABLE_IMAGE_SOURCES_MAP = {}  # set by VarietyWindow at start

    class SourceType:
        # local files and folders
        IMAGE = "image"
        FOLDER = "folder"
        ALBUM_FILENAME = "album (by filename)"
        ALBUM_DATE = "album (by date)"

        # special local folders
        FAVORITES = "favorites"
        FETCHED = "fetched"

        # predefined configurable sources
        FLICKR = "flickr"

        WALLHAVEN = "wallhaven"

        BUILTIN_SOURCE_TYPES = {
            IMAGE,
            FOLDER,
            ALBUM_FILENAME,
            ALBUM_DATE,
            FAVORITES,
            FETCHED,
            FLICKR,
        }

        LOCAL_PATH_TYPES = {IMAGE, FOLDER, ALBUM_FILENAME, ALBUM_DATE}

        LOCAL_TYPES = {IMAGE, FOLDER, ALBUM_FILENAME, ALBUM_DATE, FAVORITES, FETCHED}

        DL_TYPES = {FLICKR}

        EDITABLE_DL_TYPES = {FLICKR}

        REMOVABLE_TYPES = {FOLDER, IMAGE, ALBUM_FILENAME, ALBUM_DATE} | EDITABLE_DL_TYPES

    class LightnessMode:
        DARK = 0
        LIGHT = 1

    def __init__(self):
        self.configfile = os.path.join(get_profile_path(), "variety.conf")

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
                self.safe_mode = config["safe_mode"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.download_folder = os.path.expanduser(config["download_folder"])
            except Exception:
                pass

            try:
                self.download_preference_ratio = max(
                    0, min(1, float(config["download_preference_ratio"]))
                )
            except Exception:
                pass

            try:
                self.quota_enabled = config["quota_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.quota_size = max(50, int(config["quota_size"]))
            except Exception:
                pass

            try:
                self.favorites_folder = os.path.expanduser(config["favorites_folder"])
            except Exception:
                pass

            try:
                favorites_ops_text = config["favorites_operations"]
                self.favorites_operations = list(
                    [x.strip().split(":") for x in favorites_ops_text.split(";") if x]
                )
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
                self.clipboard_use_whitelist = (
                    config["clipboard_use_whitelist"].lower() in TRUTH_VALUES
                )
            except Exception:
                pass

            try:
                self.clipboard_hosts = config["clipboard_hosts"].lower().split(",")
            except Exception:
                pass

            try:
                icon = config["icon"]
                if icon in ["Light", "Dark", "Current", "1", "2", "3", "4", "None"] or (
                    os.access(icon, os.R_OK) and Util.is_image(icon)
                ):
                    self.icon = icon
            except Exception:
                pass

            try:
                self.desired_color_enabled = config["desired_color_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.desired_color = list(map(int, config["desired_color"].split()))
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
                self.smart_notice_shown = config["smart_notice_shown"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.smart_register_shown = config["smart_register_shown"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.stats_notice_shown = config["stats_notice_shown"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.smart_enabled = config["smart_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.sync_enabled = config["sync_enabled"].lower() in TRUTH_VALUES
            except Exception:
                pass

            try:
                self.stats_enabled = config["stats_enabled"].lower() in TRUTH_VALUES
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
                self.quotes_text_color = list(map(int, config["quotes_text_color"].split()))
                for i, x in enumerate(self.quotes_text_color):
                    self.quotes_text_color[i] = max(0, min(255, x))
            except Exception:
                pass

            try:
                self.quotes_bg_color = list(map(int, config["quotes_bg_color"].split()))
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
                self.quotes_text_color = list(map(int, config["quotes_text_color"].split()))
                for i, x in enumerate(self.quotes_text_color):
                    self.quotes_text_color[i] = max(0, min(255, x))
            except Exception:
                pass

            try:
                self.quotes_disabled_sources = config["quotes_disabled_sources"].strip().split("|")
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
                self.quotes_max_length = int(config["quotes_max_length"])
                self.quotes_max_length = max(0, self.quotes_max_length)
            except Exception:
                pass

            try:
                self.quotes_favorites_file = os.path.expanduser(config["quotes_favorites_file"])
            except Exception:
                pass

            try:
                self.slideshow_sources_enabled = (
                    config["slideshow_sources_enabled"].lower() in TRUTH_VALUES
                )
            except Exception:
                pass

            try:
                self.slideshow_favorites_enabled = (
                    config["slideshow_favorites_enabled"].lower() in TRUTH_VALUES
                )
            except Exception:
                pass

            try:
                self.slideshow_downloads_enabled = (
                    config["slideshow_downloads_enabled"].lower() in TRUTH_VALUES
                )
            except Exception:
                pass

            try:
                self.slideshow_custom_enabled = (
                    config["slideshow_custom_enabled"].lower() in TRUTH_VALUES
                )
            except Exception:
                pass

            try:
                custom_path = config["slideshow_custom_folder"]
                if custom_path in ("None", "Default") or not os.path.isdir(custom_path):
                    self.slideshow_custom_folder = Util.get_xdg_pictures_folder()
                else:
                    self.slideshow_custom_folder = custom_path
            except Exception:
                pass

            try:
                slideshow_sort_order = config["slideshow_sort_order"]
                if slideshow_sort_order in [
                    "Random",
                    "Name, asc",
                    "Name, desc",
                    "Date, asc",
                    "Date, desc",
                ]:
                    self.slideshow_sort_order = slideshow_sort_order
            except Exception:
                pass

            try:
                self.slideshow_monitor = config["slideshow_monitor"]
            except Exception:
                pass

            try:
                slideshow_mode = config["slideshow_mode"]
                if slideshow_mode in ["Fullscreen", "Desktop", "Maximized", "Window"]:
                    self.slideshow_mode = slideshow_mode
            except Exception:
                pass

            try:
                self.slideshow_seconds = float(config["slideshow_seconds"])
                self.slideshow_seconds = max(0.5, self.slideshow_seconds)
            except Exception:
                pass

            try:
                self.slideshow_fade = float(config["slideshow_fade"])
                self.slideshow_fade = max(0, min(1, self.slideshow_fade))
            except Exception:
                pass

            try:
                self.slideshow_zoom = float(config["slideshow_zoom"])
                self.slideshow_zoom = max(0, min(1, self.slideshow_zoom))
            except Exception:
                pass

            try:
                self.slideshow_pan = float(config["slideshow_pan"])
                self.slideshow_pan = max(0, min(0.20, self.slideshow_pan))
            except Exception:
                pass

            self.sources = []
            if "sources" in config:
                sources = config["sources"]
                for v in sources.values():
                    try:
                        self.sources.append(Options.parse_source(v))
                    except Exception:
                        logger.debug(lambda: "Cannot parse source: " + v, exc_info=True)
                        logger.info("Ignoring no longer supported source %s", v)

            # automatically append sources for all simple downloaders we have
            source_types = set(s[1] for s in self.sources)
            for downloader in sorted(self.SIMPLE_DOWNLOADERS, key=lambda dl: dl.get_source_type()):
                if downloader.get_source_type() not in source_types:
                    self.sources.append(
                        [True, downloader.get_source_type(), downloader.get_description()]
                    )

            self.parse_autosources()

            if "filters" in config:
                self.filters = []
                filters = config["filters"]
                for v in filters.values():
                    try:
                        self.filters.append(Options.parse_filter(v))
                    except Exception:
                        logger.exception(lambda: "Cannot parse filter: " + str(v))

            self.parse_autofilters()

            if needs_writing:
                logger.info(lambda: "Some outdated settings were updated, writing the changes")
                self.write()

        except Exception:
            logger.exception(lambda: "Could not read configuration:")

    def fix_outdated(self, config):
        changed = False
        for key, outdated_hashes in Options.OUTDATED_HASHES.items():
            if key in config:
                current_hash = hashlib.md5(config[key].encode()).hexdigest()
                if current_hash in outdated_hashes:
                    # entry is outdated: delete it and use the default
                    logger.warning(
                        lambda: "Option " + key + " has an outdated value, using the new default"
                    )
                    changed = True
                    del config[key]
        return changed

    def parse_autosources(self):
        try:
            with open(varietyconfig.get_data_file("config", "sources.txt"), encoding="utf8") as f:
                for line in f:
                    if not line.strip() or line.strip().startswith("#"):
                        continue
                    try:
                        s = Options.parse_source(line.strip())
                        if s[1] in [src[1] for src in self.sources]:
                            continue
                        self.sources.append(s)
                    except Exception:
                        logger.exception(lambda: "Cannot parse source in sources.txt: " + line)
        except Exception:
            logger.exception(lambda: "Cannot open sources.txt")

    def parse_autofilters(self):
        try:
            with open(varietyconfig.get_data_file("config", "filters.txt"), encoding="utf8") as f:
                for line in f:
                    if not line.strip() or line.strip().startswith("#"):
                        continue
                    try:
                        s = Options.parse_filter(line.strip())
                        if not s[1].lower() in [f[1].lower() for f in self.filters]:
                            self.filters.append(s)
                    except Exception:
                        logger.exception(lambda: "Cannot parse filter in filters.txt: " + line)
        except Exception:
            logger.exception(lambda: "Cannot open filters.txt")

    @staticmethod
    def parse_source(v):
        s = v.strip().split("|")
        enabled = s[0].lower() in TRUTH_VALUES
        return [enabled, s[1], s[2]]

    @staticmethod
    def parse_filter(v):
        s = v.strip().split("|")
        enabled = s[0].lower() in TRUTH_VALUES
        return [enabled, s[1], s[2]]

    @staticmethod
    def get_all_supported_source_types():
        return Options.SourceType.BUILTIN_SOURCE_TYPES | Options.get_plugin_source_types()

    @staticmethod
    def get_downloader_source_types():
        return Options.SourceType.DL_TYPES | Options.get_plugin_source_types()

    @staticmethod
    def get_editable_source_types():
        return Options.SourceType.EDITABLE_DL_TYPES | Options.get_configurable_plugin_source_types()

    @staticmethod
    def get_removable_source_types():
        return Options.SourceType.REMOVABLE_TYPES | Options.get_editable_source_types()

    @staticmethod
    def get_plugin_source_types():
        return set(dl.get_source_type() for dl in Options.IMAGE_SOURCES)

    @staticmethod
    def get_configurable_plugin_source_types():
        return set(dl.get_source_type() for dl in Options.CONFIGURABLE_IMAGE_SOURCES)

    def set_defaults(self):
        self.change_enabled = True
        self.change_on_start = False
        self.change_interval = 300
        self.safe_mode = False

        self.download_folder = os.path.join(get_profile_path(), "Downloaded")
        self.download_preference_ratio = 0.9
        self.quota_enabled = True
        self.quota_size = 1000

        self.favorites_folder = os.path.join(get_profile_path(), "Favorites")
        self.favorites_operations = [
            ["Downloaded", "Copy"],
            ["Fetched", "Move"],
            ["Others", "Copy"],
        ]

        self.fetched_folder = os.path.join(get_profile_path(), "Fetched")
        self.clipboard_enabled = False
        self.clipboard_use_whitelist = True
        self.clipboard_hosts = "wallhaven.cc,ns223506.ovh.net,wallpapers.net,flickr.com,imgur.com,deviantart.com,interfacelift.com,vladstudio.com".split(
            ","
        )

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

        self.smart_notice_shown = False
        self.smart_register_shown = False
        self.stats_notice_shown = False

        self.smart_enabled = False
        self.sync_enabled = False
        self.stats_enabled = False

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
        self.quotes_max_length = 250
        self.quotes_favorites_file = os.path.join(get_profile_path(), "favorite_quotes.txt")

        self.slideshow_sources_enabled = True
        self.slideshow_favorites_enabled = True
        self.slideshow_downloads_enabled = False
        self.slideshow_custom_enabled = False
        self.slideshow_custom_folder = Util.get_xdg_pictures_folder()
        self.slideshow_sort_order = "Random"
        self.slideshow_monitor = "All"
        self.slideshow_mode = "Fullscreen"
        self.slideshow_seconds = 6
        self.slideshow_fade = 0.4
        self.slideshow_zoom = 0.2
        self.slideshow_pan = 0.05

        self.sources = [
            [True, Options.SourceType.FAVORITES, "The Favorites folder"],
            [True, Options.SourceType.FETCHED, "The Fetched folder"],
            [True, Options.SourceType.FOLDER, "/usr/share/backgrounds/"],
            [
                True,
                Options.SourceType.FLICKR,
                "user:www.flickr.com/photos/peter-levi/;user_id:93647178@N00;",
            ],
        ]

        self.filters = [
            [False, "Keep original", ""],
            [False, "Grayscale", "-type Grayscale"],
            [False, "Heavy blur", "-blur 120x40"],
            [False, "Oil painting", "-paint 6"],
            [False, "Charcoal painting", "-charcoal 3"],
            [False, "Pointilism", "-spread 10 -noise 3"],
            [False, "Pixellate", "-scale 3% -scale 3333%"],
        ]

    def write(self):
        try:
            config = ConfigObj(self.configfile, encoding="utf8", default_encoding="utf8")
        except Exception:
            config = ConfigObj(encoding="utf8", default_encoding="utf8")
            config.filename = self.configfile

        try:
            config["change_enabled"] = str(self.change_enabled)
            config["change_on_start"] = str(self.change_on_start)
            config["change_interval"] = str(self.change_interval)
            config["safe_mode"] = str(self.safe_mode)

            config["download_folder"] = Util.collapseuser(self.download_folder)
            config["download_preference_ratio"] = str(self.download_preference_ratio)

            config["quota_enabled"] = str(self.quota_enabled)
            config["quota_size"] = str(self.quota_size)

            config["favorites_folder"] = Util.collapseuser(self.favorites_folder)
            config["favorites_operations"] = ";".join(
                ":".join(x) for x in self.favorites_operations
            )

            config["fetched_folder"] = Util.collapseuser(self.fetched_folder)
            config["clipboard_enabled"] = str(self.clipboard_enabled)
            config["clipboard_use_whitelist"] = str(self.clipboard_use_whitelist)
            config["clipboard_hosts"] = ",".join(self.clipboard_hosts)

            config["icon"] = self.icon

            config["desired_color_enabled"] = str(self.desired_color_enabled)
            config["desired_color"] = (
                " ".join(map(str, self.desired_color)) if self.desired_color else "None"
            )
            config["min_size_enabled"] = str(self.min_size_enabled)
            config["min_size"] = str(self.min_size)
            config["use_landscape_enabled"] = str(self.use_landscape_enabled)
            config["lightness_enabled"] = str(self.lightness_enabled)
            config["lightness_mode"] = str(self.lightness_mode)
            config["min_rating_enabled"] = str(self.min_rating_enabled)
            config["min_rating"] = str(self.min_rating)

            config["smart_notice_shown"] = str(self.smart_notice_shown)
            config["smart_register_shown"] = str(self.smart_register_shown)
            config["stats_notice_shown"] = str(self.stats_notice_shown)

            config["smart_enabled"] = str(self.smart_enabled)
            config["sync_enabled"] = str(self.sync_enabled)
            config["stats_enabled"] = str(self.stats_enabled)

            config["copyto_enabled"] = str(self.copyto_enabled)
            config["copyto_folder"] = Util.collapseuser(self.copyto_folder)

            config["clock_enabled"] = str(self.clock_enabled)
            config["clock_filter"] = self.clock_filter
            config["clock_font"] = self.clock_font
            config["clock_date_font"] = self.clock_date_font

            config["quotes_enabled"] = str(self.quotes_enabled)
            config["quotes_font"] = self.quotes_font
            config["quotes_text_color"] = " ".join(map(str, self.quotes_text_color))
            config["quotes_bg_color"] = " ".join(map(str, self.quotes_bg_color))
            config["quotes_bg_opacity"] = str(self.quotes_bg_opacity)
            config["quotes_text_shadow"] = str(self.quotes_text_shadow)
            config["quotes_disabled_sources"] = "|".join(self.quotes_disabled_sources)
            config["quotes_tags"] = self.quotes_tags
            config["quotes_authors"] = self.quotes_authors
            config["quotes_change_enabled"] = str(self.quotes_change_enabled)
            config["quotes_change_interval"] = str(self.quotes_change_interval)
            config["quotes_width"] = str(self.quotes_width)
            config["quotes_hpos"] = str(self.quotes_hpos)
            config["quotes_vpos"] = str(self.quotes_vpos)
            config["quotes_max_length"] = str(self.quotes_max_length)
            config["quotes_favorites_file"] = Util.collapseuser(self.quotes_favorites_file)

            config["slideshow_sources_enabled"] = str(self.slideshow_sources_enabled)
            config["slideshow_favorites_enabled"] = str(self.slideshow_favorites_enabled)
            config["slideshow_downloads_enabled"] = str(self.slideshow_downloads_enabled)
            config["slideshow_custom_enabled"] = str(self.slideshow_custom_enabled)
            config["slideshow_custom_folder"] = Util.collapseuser(self.slideshow_custom_folder)
            config["slideshow_sort_order"] = self.slideshow_sort_order
            config["slideshow_monitor"] = self.slideshow_monitor
            config["slideshow_mode"] = self.slideshow_mode
            config["slideshow_seconds"] = str(self.slideshow_seconds)
            config["slideshow_fade"] = str(self.slideshow_fade)
            config["slideshow_zoom"] = str(self.slideshow_zoom)
            config["slideshow_pan"] = str(self.slideshow_pan)

            config["sources"] = {}
            for i, s in enumerate(self.sources):
                config["sources"]["src" + str(i + 1)] = str(s[0]) + "|" + str(s[1]) + "|" + s[2]

            config["filters"] = {}
            for i, f in enumerate(self.filters):
                config["filters"]["filter" + str(i + 1)] = str(f[0]) + "|" + f[1] + "|" + f[2]

            config.write()

        except Exception:
            logger.exception(lambda: "Could not write configuration:")

    @staticmethod
    def set_options(opts):
        config = Options().read_config()
        for key, value in opts:
            config[key] = value
        config.write()

    def read_config(self):
        config = ConfigObj(raise_errors=False, encoding="utf8", default_encoding="utf8")
        config.filename = self.configfile
        try:
            config.reload()
        except DuplicateError:
            logger.warning(lambda: "Duplicate keys in config file, please fix this")
        return config


if __name__ == "__main__":
    formatter = logging.Formatter("%(levelname)s:%(name)s: %(funcName)s() '%(message)s'")

    logger = logging.getLogger("variety")
    logger_sh = logging.StreamHandler()
    logger_sh.setFormatter(formatter)
    logger.addHandler(logger_sh)

    o = Options()
    o.read()
    print(o.sources)
    print(o.filters)
    o.write()
