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
from functools import reduce

from variety.plugins.downloaders.SimpleDownloader import SimpleDownloader
from variety.Util import Util, _

DATA_URL = "https://knokfirst.com/behang_manifest.json"

logger = logging.getLogger("variety")


class BehangDownloader(SimpleDownloader):
    DESCRIPTION = _("Behang wallpapers")
    ROOT_URL = "http://knokfirst.com/behang/"

    @classmethod
    def get_info(cls):
        return {
            "name": "BehangDownloader",
            "description": BehangDownloader.DESCRIPTION,
            "author": "Eric Rösch",
            "version": "0.1",
        }

    def get_description(self):
        return BehangDownloader.DESCRIPTION

    def get_source_type(self):
        return "behang"

    def get_source_name(self):
        return "Behang"

    def get_source_location(self):
        return self.ROOT_URL

    def fill_queue(self):
        queue = Util.fetch_json(DATA_URL)
        images = queue["wallpapers"]["category"]
        images = list(map(lambda x: x["wallpaper"], images))
        images = reduce(lambda x, y: x + y, images)
        random.shuffle(images)
        return images

    def download_queue_item(self, item):
        origin_url = BehangDownloader.ROOT_URL
        image_url = item["url"]
        return self.save_locally(origin_url, image_url)
