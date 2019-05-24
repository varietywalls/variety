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
import shutil

from variety import _

logger = logging.getLogger('variety')

from variety.plugins.downloaders.SimpleDownloader import SimpleDownloader


EARTH_IMAGE_URL = "https://static.die.net/earth/mercator/1600.jpg"
EARTH_ORIGIN_URL = "https://www.die.net/earth/"
EARTH_FILENAME = "earth--refreshable.jpg"


class EarthDownloader(SimpleDownloader):
    DESCRIPTION = _("World Sunlight Map - live wallpaper from Die.net")

    @classmethod
    def get_info(cls):
        return {
            "name": "EarthDownloader",
            "description": EarthDownloader.DESCRIPTION,
            "author": "Peter Levi",
            "version": "0.1"
        }

    def get_source_type(self):
        return "earth"

    def get_description(self):
        return EarthDownloader.DESCRIPTION

    def get_source_name(self):
        return "Die.net"

    def get_folder_name(self):
        return "Earth"

    def get_source_location(self):
        return EARTH_ORIGIN_URL

    def get_refresh_interval_seconds(self):
        return 15 * 60

    def download_one(self):
        logger.info(lambda: "Downloading world sunlight map from " + EARTH_ORIGIN_URL)
        downloaded = self.save_locally(
            EARTH_ORIGIN_URL,
            EARTH_IMAGE_URL,
            force_download=True,
            extra_metadata={'headline': 'World Sunlight Map'},
        )
        final_path = os.path.join(self.target_folder, EARTH_FILENAME)
        shutil.move(downloaded, final_path)
        for f in os.listdir(self.target_folder):
            if f != EARTH_FILENAME and f.lower().endswith(".jpg"):
                os.unlink(os.path.join(self.target_folder, f))
        return final_path

    def fill_queue(self):
        """ Not needed here """
        return []

    def on_variety_start_complete(self):
        if not os.path.exists(os.path.join(self.target_folder, EARTH_FILENAME)):
            self.download_one()
