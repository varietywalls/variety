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
import time

from variety.plugins.downloaders.ImageSource import Throttling
from variety.plugins.downloaders.SimpleDownloader import SimpleDownloader
from variety.Util import Util, _

logger = logging.getLogger("variety")

random.seed()


class UnsplashDownloader(SimpleDownloader):
    DESCRIPTION = _("High-resolution photos from Unsplash.com")

    API_KEY = "37ee4be36ffd27e79decd4ef382d4949"
    HASH = (
        b"AwBXAAFSUQtSAAUGBQQED11dBAdRDQMFVQwCVgAOBQwCDwMDDAYDBARTAgIGAVdVCQdRBQUCU1NV\n"
        b"DARSAQgBWA==\n"
    )
    UTM_PARAMS = "?utm_source=Variety+Wallpaper+Changer&utm_medium=referral"

    rate_limiting_started_time = 0

    @classmethod
    def get_info(cls):
        return {
            "name": "UnsplashDownloader",
            "description": UnsplashDownloader.DESCRIPTION,
            "author": "Peter Levi",
            "version": "0.1",
        }

    def get_source_type(self):
        return "unsplash"

    def get_description(self):
        return UnsplashDownloader.DESCRIPTION

    def get_source_name(self):
        return "Unsplash.com"

    def get_source_location(self):
        return "https://unsplash.com"

    def get_folder_name(self):
        return "Unsplash"

    def get_server_options_key(self):
        return "unsplash_v2"

    def get_default_throttling(self):
        return Throttling(max_downloads_per_hour=10, max_queue_fills_per_hour=1)

    def get_unsplash_api_url(self):
        return "https://api.unsplash.com/photos/random?count=30&client_id={}{}".format(
            Util.unxor(UnsplashDownloader.HASH, UnsplashDownloader.API_KEY),
            "&orientation=landscape" if self.get_variety().options.use_landscape_enabled else "",
        )

    def fill_queue(self):
        if time.time() - UnsplashDownloader.rate_limiting_started_time < 3600:
            logger.info(
                lambda: "Unsplash queue empty, but rate limit reached, will try again later"
            )
            return []

        url = self.get_unsplash_api_url()
        logger.info(lambda: "Filling Unsplash queue from " + url)

        r = Util.request(url)
        if int(r.headers.get("X-Ratelimit-Remaining", 1000000)) < 1000:
            UnsplashDownloader.rate_limiting_started_time = time.time()

        queue = []
        for item in r.json():
            try:
                width = item["width"]
                height = item["height"]
                if self.is_size_inadequate(width, height):
                    continue

                image_url = item["urls"]["full"] + "&w={}".format(
                    max(1980, int(Util.get_screen_width() * 1.2))
                )
                origin_url = item["links"]["html"] + UnsplashDownloader.UTM_PARAMS

                extra_metadata = {
                    "sourceType": "unsplash",
                    "sfwRating": 100,
                    "author": item["user"]["name"],
                    "authorURL": item["user"]["links"]["html"] + UnsplashDownloader.UTM_PARAMS,
                    "keywords": [cat["title"].lower().strip() for cat in item["categories"]],
                    "extraData": {
                        "unsplashDownloadLocation": item["links"]["download_location"],
                        "unsplashDownloadReported": False,
                    },
                }

                queue.append((origin_url, image_url, extra_metadata))
            except:
                logger.exception(lambda: "Could not process an item from Unsplash")
                raise

        random.shuffle(queue)
        return queue

    def on_image_set_as_wallpaper(self, img, meta):
        extraData = meta.get("extraData", None)
        if not extraData:
            return

        download_loc = extraData.get("unsplashDownloadLocation")
        reported = extraData.get("unsplashDownloadReported")
        if download_loc and not reported:
            url = "{}?client_id={}".format(
                download_loc, Util.unxor(UnsplashDownloader.HASH, UnsplashDownloader.API_KEY)
            )
            Util.fetch(url)
            meta["extraData"]["unsplashDownloadReported"] = True
            Util.write_metadata(img, meta)
