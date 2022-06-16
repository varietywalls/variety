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

import requests

from variety.plugins.builtin.downloaders.WallhavenLegacyDownloader import WallhavenLegacyDownloader
from variety.plugins.downloaders.DefaultDownloader import DefaultDownloader
from variety.Util import Util, _

API_SEARCH = "https://wallhaven.cc/api/v1/search"
API_SAFE_SEARCH_URL = (
    "https://wallhaven.cc/api/v1/search?q=%s&categories=111&purity=100&sorting=favorites&order=desc"
)
WEB_DOMAIN_SEARCH = "https://wallhaven.cc/search"
WALLPAPER_INFO_URL = "https://wallhaven.cc/api/v1/w/%s"

logger = logging.getLogger("variety")

random.seed()


class BadApiKeyException(Exception):
    pass


class WallhavenDownloader(DefaultDownloader):
    def __init__(self, source, location, api_key):
        DefaultDownloader.__init__(self, source=source, config=location)
        self.api_key = api_key
        self.legacy_downloader = WallhavenLegacyDownloader(source, location)
        self.parse_location()

    def update_download_folder(self, global_download_folder):
        target_folder = super().update_download_folder(global_download_folder)
        self.legacy_downloader.target_folder = target_folder
        self.legacy_downloader.state = self.state
        return target_folder

    def parse_location(self):
        if not self.config.startswith(("http://", "https://")):
            # interpret location as keywords
            self.api_url = API_SAFE_SEARCH_URL % self.config
        else:
            # location is an URL, use it
            url = self.config.replace("http://", "https://")

            # Use Wallhaven API
            if url.startswith(API_SEARCH):
                self.api_url = url
            elif url.startswith(WEB_DOMAIN_SEARCH):
                self.api_url = url.replace(WEB_DOMAIN_SEARCH, API_SEARCH)
            elif url.startswith("https://wallhaven.cc/tag"):
                self.api_url = url.replace(
                    "https://wallhaven.cc/tag/", "https://wallhaven.cc/api/v1/search?q=id:"
                )
            else:
                # we'll fallback to WallhavenLegacyDownloader
                self.api_url = None

        # make sure we use the API key, if provided
        if self.api_url and self.api_key and "&apikey=" not in self.api_url:
            self.api_url += "&apikey=" + self.api_key

    def search(self, page=None):
        if not self.api_url:
            return self.legacy_downloader.search(page)

        url = self.api_url
        if page:
            url = url + ("&" if "?" in self.api_url else "?") + "page=" + str(page)
        logger.info(lambda: "Performing wallhaven search: url=%s" % url)
        response = Util.fetch_json(url)
        count = response["meta"]["total"]
        return response, count

    @staticmethod
    def validate(location, api_key):
        logger.info(lambda: "Validating Wallhaven location " + location)
        try:
            _, count = WallhavenDownloader(None, location, api_key).search()
            return count > 0
        except requests.HTTPError as e:
            if api_key and e.response.status_code == 401:
                raise BadApiKeyException()
        except Exception:
            pass

        try:
            return WallhavenLegacyDownloader.validate(location)
        except:
            logger.exception(lambda: "Error while validating Wallhaven search")
            return False

    def download_queue_item(self, queue_item):
        if not self.api_url:
            return self.legacy_downloader.download_queue_item(queue_item)

        wallpaper_url = queue_item["url"]
        logger.info(lambda: "Wallpaper URL: " + wallpaper_url)

        src_url = queue_item["path"]
        logger.info(lambda: "Image src URL: " + src_url)

        extra_metadata = {}
        try:
            wallpaper_info = Util.fetch_json(
                WALLPAPER_INFO_URL % urllib.parse.quote(queue_item["id"])
            )
            extra_metadata["keywords"] = [tag["name"] for tag in wallpaper_info["data"]["tags"]]
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
        if not self.api_url:
            return self.legacy_downloader.fill_queue()

        queue = []

        not_random = "sorting=random" not in self.api_url
        if not_random:
            s, count = self.search()
            pages = min(count, 1000) // int(s["meta"]["per_page"]) + 1
            page = random.randint(1, pages)
            logger.info(lambda: "%s wallpapers in result, using page %s" % (count, page))
            s, _ = self.search(page=page)
        else:
            s, _ = self.search()

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
