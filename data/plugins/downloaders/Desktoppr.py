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
from variety.Util import Util
from variety.plugins.ISimpleDownloader import ISimpleDownloader

logger = logging.getLogger('variety')


class Desktoppr(ISimpleDownloader):
    def get_source_type(self):
        return "desktoppr"

    def get_source_name(self):
        return "Desktoppr"

    def get_description(self):
        return "Random wallpapers from Desktoppr.co"

    def get_folder_name(self):
        return "Desktoppr"

    def download_one(self):
        logger.info(lambda: "Downloading a random image from desktoppr.co")

        response = Util.fetch_json("https://api.desktoppr.co/1/wallpapers/random")

        if response["response"]["review_state"] != "safe":
            logger.info(lambda: "Non-safe image returned by Desktoppr, skipping")
            return None

        origin_url = response["response"]["url"]
        image_url = response["response"]["image"]["url"]

        return self.save_locally(origin_url, image_url)
