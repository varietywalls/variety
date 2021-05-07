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
from os.path import basename, splitext

from variety.plugins.downloaders.SimpleDownloader import SimpleDownloader
from variety.Util import Util, _

DATA_URL = "https://www.nationalgeographic.co.uk/page-data/photo-of-day/page-data.json"

logger = logging.getLogger("variety")


class NationalGeographicDownloader(SimpleDownloader):
    DESCRIPTION = _("National Geographic's photo of the day")
    ROOT_URL = "https://www.nationalgeographic.co.uk/photo-of-day"

    @classmethod
    def get_info(cls):
        return {
            "name": "NationalGeographicDownloader",
            "description": NationalGeographicDownloader.DESCRIPTION,
            "author": "Eric Rösch",
            "version": "0.1",
        }

    def get_description(self):
        return NationalGeographicDownloader.DESCRIPTION

    def get_source_type(self):
        return "natgeo"

    def get_source_name(self):
        return "National Geographic"

    def get_source_location(self):
        return self.ROOT_URL

    def fill_queue(self):
        queue = Util.fetch_json(DATA_URL)
        images = queue["result"]["pageContext"]["node"]["data"]["content"]["images"]
        return images

    def download_queue_item(self, item):
        url = item["entity"]["mediaImage"]["url"]
        origin_url = NationalGeographicDownloader.ROOT_URL + "?image=" + splitext(basename(url))[0]
        image_url = "https://static.nationalgeographic.co.uk" + url
        return self.save_locally(origin_url, image_url)
