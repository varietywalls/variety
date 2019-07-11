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

logger = logging.getLogger("variety")

random.seed()


class APODDownloader(SimpleDownloader):
    DESCRIPTION = _("NASA Astro Pic of the Day")
    ROOT_URL = "http://apod.nasa.gov/apod/"

    @classmethod
    def get_info(cls):
        return {
            "name": "APODDownloader",
            "description": APODDownloader.DESCRIPTION,
            "author": "Peter Levi",
            "version": "0.1",
        }

    def get_description(self):
        return APODDownloader.DESCRIPTION

    def get_source_type(self):
        return "apod"

    def get_source_name(self):
        return "NASA Astro Pic of the Day"

    def get_folder_name(self):
        return "nasa_apod"

    def get_source_location(self):
        return self.ROOT_URL

    def fill_queue(self):
        logger.info(lambda: "Filling APOD queue from Archive")

        s = Util.html_soup(self.ROOT_URL + "archivepix.html")
        urls = [
            self.ROOT_URL + x["href"]
            for x in s.findAll("a")
            if x["href"].startswith("ap") and x["href"].endswith(".html")
        ]
        urls = urls[:730]  # leave only last 2 years' pics
        urls = [url for url in urls if not self.is_in_banned(url)]

        queue = urls[:3]  # always put the latest 3 first
        urls = urls[3:]
        random.shuffle(urls)  # shuffle the rest
        queue.extend(urls)
        return queue

    def download_queue_item(self, queue_item):
        origin_url = queue_item
        logger.info(lambda: "APOD URL: " + origin_url)

        s = Util.html_soup(origin_url)
        img_url = None
        try:
            link = s.find("img").parent["href"]
            if link.startswith("image/"):
                img_url = self.ROOT_URL + link
                logger.info(lambda: "Image URL: " + img_url)
        except Exception:
            pass

        if img_url:
            return self.save_locally(origin_url, img_url, source_location=self.ROOT_URL)
        else:
            logger.info(lambda: "No image url found for this APOD URL")
            return None
