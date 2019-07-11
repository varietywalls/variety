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

from variety import _
from variety.plugins.downloaders.SimpleDownloader import SimpleDownloader
from variety.Util import Util

MANIFEST_URL = "https://storage.googleapis.com/chromeos-wallpaper-public/manifest_en.json"

logger = logging.getLogger("variety")

random.seed()


class ChromeOSWallpapersDownloader(SimpleDownloader):
    DESCRIPTION = _("Chrome OS Wallpapers")

    @classmethod
    def get_info(cls):
        return {
            "name": "ChromeOsWallpapersDownloader",
            "description": ChromeOSWallpapersDownloader.DESCRIPTION,
            "author": "Peter Levi",
            "version": "0.1",
        }

    def get_description(self):
        return ChromeOSWallpapersDownloader.DESCRIPTION

    def get_source_type(self):
        return "chromeos"

    def get_source_name(self):
        return "Chrome OS Wallpapers"

    def get_source_location(self):
        return self.get_source_name()

    def fill_queue(self):
        manifest = Util.fetch_json(MANIFEST_URL)
        queue = manifest["wallpaper_list"]
        self.tags = manifest["tags"]
        random.shuffle(queue)
        return queue

    def download_queue_item(self, item):
        image_url = item["base_url"] + "_high_resolution.jpg"
        origin_url = item["dynamic_url"]
        extra_metadata = {}
        if "tags" in item:
            extra_metadata["keywords"] = [
                self.tags[str(tag)] for tag in item["tags"] if str(tag) in self.tags
            ]
        if "author" in item:
            extra_metadata["author"] = item["author"]
        if "author_website" in item:
            extra_metadata["authorURL"] = item["author_website"]

        return self.save_locally(origin_url, image_url, extra_metadata=extra_metadata)
