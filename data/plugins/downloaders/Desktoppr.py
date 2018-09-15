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

from variety import _
from variety.Util import Util
from variety.plugins.downloaders.SimpleDownloader import SimpleDownloader
from variety.plugins.downloaders.DefaultDownloader import QueueItem

logger = logging.getLogger('variety')


class Desktoppr(SimpleDownloader):
    DESCRIPTION = _("Random wallpapers from Desktoppr.co")

    @classmethod
    def get_info(cls):
        return {
            "name": "Desktoppr",
            "description": Desktoppr.DESCRIPTION,
            "author": "Peter Levi",
            "version": "0.1"
        }

    def __init__(self):
        SimpleDownloader.__init__(
            self,
            source_type="desktoppr",
            description=Desktoppr.DESCRIPTION,
            folder_name="Desktoppr")

    def get_source_name(self):
        return "Desktoppr.co"

    def fill_queue(self):
        response = Util.fetch_json("https://api.desktoppr.co/1/wallpapers/random")

        if response["response"]["review_state"] != "safe":
            logger.info(lambda: "Non-safe image returned by Desktoppr, skipping")
            return None

        origin_url = response["response"]["url"]
        image_url = response["response"]["image"]["url"]
        return [QueueItem(origin_url, image_url, {})]
