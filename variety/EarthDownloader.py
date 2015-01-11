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
import os
import subprocess

logger = logging.getLogger('variety')

from variety import Downloader

EARTH_IMAGE_URL = "http://static.die.net/earth/mercator/1600.jpg"
EARTH_ORIGIN_URL = "http://www.die.net/earth/"
EARTH_FILENAME = "earth.jpg"

class EarthDownloader(Downloader.Downloader):
    def __init__(self, parent):
        super(EarthDownloader, self).__init__(
            parent, "earth", "Die.net", EARTH_ORIGIN_URL, is_refresher=True)

    def convert_to_filename(self, url):
        return "Earth"

    def download_one(self):
        logger.info(lambda: "Downloading world sunlight map from " + EARTH_ORIGIN_URL)
        downloaded = self.save_locally(self.location, EARTH_IMAGE_URL, force_download=True, extra_metadata={'headline': 'World Sunlight Map'})
        cropped = os.path.join(self.target_folder, EARTH_FILENAME)
        subprocess.call(["convert", downloaded, "-gravity", "north", "-crop", "100%x95%", cropped])
        for f in os.listdir(self.target_folder):
            if f != EARTH_FILENAME and f.lower().endswith(".jpg"):
                os.unlink(os.path.join(self.target_folder, f))
        return cropped

