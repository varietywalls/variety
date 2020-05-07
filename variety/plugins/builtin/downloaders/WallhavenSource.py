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
import logging
import random

from variety.plugins.builtin.downloaders.WallhavenDownloader import WallhavenDownloader
from variety.plugins.downloaders.ConfigurableImageSource import ConfigurableImageSource
from variety.plugins.downloaders.ImageSource import Throttling
from variety.Util import _

logger = logging.getLogger("variety")

random.seed()


class WallhavenSource(ConfigurableImageSource):
    @classmethod
    def get_info(cls):
        return {
            "name": "WallhavenSource",
            "description": _("Configurable source for fetching images from Wallhaven.cc"),
            "author": "Peter Levi",
            "version": "0.1",
        }

    def get_source_name(self):
        return "Wallhaven.cc"

    def get_source_type(self):
        return "wallhaven"

    def get_default_throttling(self):
        return Throttling(max_downloads_per_hour=360, max_queue_fills_per_hour=40)

    def get_ui_instruction(self):
        return _(
            "<a href='http://wallhaven.cc'>Wallhaven.cc</a> provides a variety of image search options. "
            "Below you can specify keywords to search for, or visit <a href='http://wallhaven.cc'>Wallhaven.cc</a>, "
            "setup your search criteria there, ensure you like the results, and paste the full Wallhaven URL "
            "in the box.\n"
            "\n"
            "If you specify keywords, the most liked safe-for-work images that match all of the keywords will "
            "be used. \n"
            "\n"
            "If you specify a Wallhaven URL, please choose the sorting criteria carefully - Variety regularly "
            "requests images, but uses only images from the first several hundred returned. Random or Date will "
            "mean this image source will have a longer 'lifetime' till it is exhausted. Favorites will provide "
            "better images and Relevance will provide closer matches when searching for phrases or colors."
        )

    def get_ui_short_instruction(self):
        return _("Enter keywords or paste URL here: ")

    def get_ui_short_description(self):
        return _("Fetch images from Wallhaven.cc for a given criteria")

    def validate(self, query):
        valid = WallhavenDownloader.validate(query)
        return query, None if valid else _("No images found")

    def create_downloader(self, config):
        return WallhavenDownloader(self, config)
