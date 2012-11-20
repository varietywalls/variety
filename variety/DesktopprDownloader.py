# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Peter Levi <peterlevi@peterlevi.com>
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

import json
import logging
from variety import Downloader
from variety.Util import Util

logger = logging.getLogger('variety')

class DesktopprDownloader(Downloader.Downloader):
    def __init__(self, parent):
        super(DesktopprDownloader, self).__init__(
            parent, "Desktoppr.co", "https://api.desktoppr.co/1/wallpapers/random")

    def convert_to_filename(self, url):
        return "Desktoppr"

    def download_one(self):
        logger.info("Downloading a random image from desktoppr.co")

        content = Util.fetch(self.location)
        response = json.loads(content)

        if response["response"]["review_state"] != "safe":
            logger.info("Non-safe image returned by Desktoppr, skipping")
            return None

        origin_url = response["response"]["url"]
        image_url = response["response"]["image"]["url"]

        return self.save_locally(origin_url, image_url)
