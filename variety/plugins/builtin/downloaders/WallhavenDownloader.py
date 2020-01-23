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
import urllib.parse

from variety.plugins.downloaders.DefaultDownloader import DefaultDownloader
from variety.Util import Util, _

SEARCH_URL = (
    "https://wallhaven.cc/api/v1/search?q=%s&categories=111&purity=100&sorting=favorites&order=desc&"
)

WALLPAPER_INFO_URL = "https://wallhaven.cc/api/v1/w/%s"

logger = logging.getLogger("variety")

random.seed()


class WallhavenDownloader(DefaultDownloader):
    def __init__(self, source, location):
        DefaultDownloader.__init__(self, source=source, config=location)
        self.parse_location()

    def parse_location(self):
        if self.config.startswith(("http://", "https://")):
            # location is an URL, use it
            self.url = self.config.replace("http://", "https://")
        else:
            # interpret location as keywords
            self.url = SEARCH_URL % urllib.parse.quote(self.config)
            return

        # Use Wallhaven API
        if self.config.startswith("https://wallhaven.cc/search"):
            self.url = self.config.replace("https://wallhaven.cc/search", "https://wallhaven.cc/api/v1/search")
        elif self.config.startswith("https://wallhaven.cc/tag"):
            # location is an URL, use it
            self.url = self.config.replace("https://wallhaven.cc/tag/", "https://wallhaven.cc/api/v1/search?q=id:")

        self.wallpaper_info_url = WALLPAPER_INFO_URL

    def search(self, page=None):
        url = self.url

        if page:
            url = url + ("&" if "?" in self.url else "?") + "page=" + str(page)

        logger.info(lambda: "Performing wallhaven search: url=%s" % url)

        response = Util.fetch_json(url)

        result_count = None
        try:
            result_count = response["meta"]["total"]
        except:
            pass

        return response, result_count

    @staticmethod
    def validate(location):
        logger.info(lambda: "Validating Wallhaven location " + location)
        try:
            s, count = WallhavenDownloader(None, location).search()
            return count > 0
        except Exception:
            logger.exception(lambda: "Error while validating wallhaven search")
            return False

    def download_queue_item(self, queue_item):
        wallpaper_url = queue_item["url"]
        logger.info(lambda: "Wallpaper URL: " + wallpaper_url)

        src_url = queue_item["path"]
        logger.info(lambda: "Image src URL: " + src_url)

        extra_metadata = {}
        try:
            wallpaper_info = Util.fetch_json(self.wallpaper_info_url % urllib.parse.quote(queue_item["id"]))
            extra_metadata["keywords"] = [
                tag["name"] for tag in wallpaper_info["data"]["tags"]
            ]
        except:
            pass

        try:
            purity = queue_item["purity"]
            sfw_rating = {"sfw": 100, "sketchy": 50, "nsfw": 0}[purity]
            extra_metadata["sfwRating"] = sfw_rating

            if self.is_safe_mode_enabled() and sfw_rating < 100:
                logger.info(
                    lambda: "Skipping non-safe download from Wallhaven. "
                    "Is the source %s suitable for Safe mode?" % self.config
                )
                return None
        except:
            pass

        return self.save_locally(wallpaper_url, src_url, extra_metadata=extra_metadata)

    def fill_queue(self):
        queue = []

        not_random = not "sorting=random" in self.url
        if not_random:
            s, count = self.search()
            if not count:
                count = 300
            pages = min(count, 300) // 24 + 1
            page = random.randint(1, pages)
            logger.info(lambda: "%s wallpapers in result, using page %s" % (count, page))
            s, count = self.search(page=page)
        else:
            s, count = self.search()

        results = s["data"]
        for result in results:
            try:
                p = result["resolution"].split("x")
                width = p[0]
                height = p[1]
                if self.is_size_inadequate(width, height):
                    continue
            except Exception:
                # missing or unparseable resolution - consider ok
                pass

            queue.append(result)

        random.shuffle(queue)

        if not_random and len(queue) >= 20:
            queue = queue[: len(queue) // 2]
            # only use randomly half the images from the page -
            # if we ever hit that same page again, we'll still have what to download

        return queue
