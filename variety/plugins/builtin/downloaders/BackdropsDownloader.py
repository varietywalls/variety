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

from variety.plugins.downloaders.SimpleDownloader import SimpleDownloader
from variety.Util import Util, _

DATA_URL = "https://backdrops.io/walls/api_v3.2.php?task=all_walls"

logger = logging.getLogger("variety")


class BackdropsDownloader(SimpleDownloader):
    DESCRIPTION = _("Backdrops wallpapers")
    ROOT_URL = "https://backdrops.io/"

    @classmethod
    def get_info(cls):
        return {
            "name": "BackdropsDownloader",
            "description": BackdropsDownloader.DESCRIPTION,
            "author": "Eric Rösch",
            "version": "0.1",
        }

    def get_description(self):
        return BackdropsDownloader.DESCRIPTION

    def get_source_type(self):
        return "backdrops"

    def get_source_name(self):
        return "Backdrops"

    def get_source_location(self):
        return self.ROOT_URL

    def fill_queue(self):
        queue = Util.fetch_json(DATA_URL)
        images = queue["wallList"]
        random.shuffle(images)
        return images

    def download_queue_item(self, item):
        origin_url = BackdropsDownloader.ROOT_URL
        image_url = "https://backdrops.io/walls/upload/" + item["url"]
        return self.save_locally(origin_url, image_url)
