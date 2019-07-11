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
from variety.plugins.downloaders.ImageSource import Throttling
from variety.plugins.downloaders.SimpleDownloader import SimpleDownloader
from variety.Util import Util

# Credits: Using the data prepared by limhenry @ https://github.com/limhenry/earthview
DATA_URL = "https://raw.githubusercontent.com/limhenry/earthview/3cd868a932cd652c4373c0f6ea8618a96b08be4e/wallpaper%20changer/data.json"

logger = logging.getLogger("variety")

random.seed()


class EarthviewDownloader(SimpleDownloader):
    DESCRIPTION = _("Google Earth View Wallpapers")
    ROOT_URL = "https://earthview.withgoogle.com/"

    @classmethod
    def get_info(cls):
        return {
            "name": "EarthviewDownloader",
            "description": EarthviewDownloader.DESCRIPTION,
            "author": "Peter Levi",
            "version": "0.1",
        }

    def get_description(self):
        return EarthviewDownloader.DESCRIPTION

    def get_source_type(self):
        return "earthview"

    def get_source_name(self):
        return "Earth View"

    def get_source_location(self):
        return self.ROOT_URL

    def fill_queue(self):
        queue = Util.fetch_json(DATA_URL)
        random.shuffle(queue)
        return queue

    def get_default_throttling(self):
        # throttle this source, as otherwise maps "overpower" all other types of images
        # with Variety's default settings, and we have no other way to control source "weights"
        return Throttling(min_download_interval=600, min_fill_queue_interval=0)

    def download_queue_item(self, item):
        region = item["Region"]
        filename = "{}{} (ID-{}).jpg".format(
            region + ", " if region and region != "-" else "", item["Country"], item["ID"]
        )
        origin_url = EarthviewDownloader.ROOT_URL + str(item["ID"])
        image_url = item["Image URL"]
        if not image_url.startswith("http"):
            image_url = "https://" + image_url
        return self.save_locally(origin_url, image_url, local_filename=filename)
