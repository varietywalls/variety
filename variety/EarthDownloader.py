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

import logging

logger = logging.getLogger('variety')

from variety import Downloader

EARTH_IMAGE_URL = "http://static.die.net/earth/mercator/1600.jpg"
EARTH_ORIGIN_URL = "http://www.die.net/earth/"

class EarthDownloader(Downloader.Downloader):
    def __init__(self, parent):
        super(EarthDownloader, self).__init__(
            parent, "World Sunlight Map", EARTH_ORIGIN_URL)

    def convert_to_filename(self, url):
        return "Earth"

    def download_one(self):
        logger.info("Downloading world sunlight map from " + EARTH_ORIGIN_URL)
        return self.save_locally(self.location, EARTH_IMAGE_URL, force_download=True)
