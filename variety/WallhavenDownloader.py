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
from variety.plugins.downloaders.ImageSource import ImageSource, Throttling
from variety.Util import Util, _

SEARCH_URL = (
    "https://wallhaven.cc/search?q=%s&categories=111&purity=100&sorting=favorites&order=desc"
)

logger = logging.getLogger("variety")

random.seed()


class WallhavenDownloader(ImageSource, DefaultDownloader):
    def __init__(self, parent, location):
        ImageSource.__init__(self)
        DefaultDownloader.__init__(self, source=self, config=location)
        self.set_variety(parent)
        self.parse_location()

    @classmethod
    def get_info(cls):
        raise Exception("Not yet implemented as a plugin")

    def get_description(self):
        return _("Images from Wallhaven.cc")

    def get_source_name(self):
        return "Wallhaven.cc"

    def get_source_type(self):
        return "wallhaven"

    def get_default_throttling(self):
        return Throttling(max_downloads_per_hour=180, max_queue_fills_per_hour=20)

    def parse_location(self):
        if self.config.startswith(("http://", "https://")):
            # location is an URL, use it
            self.url = self.config.replace("http://", "https://")
        else:
            # interpret location as keywords
            self.url = SEARCH_URL % urllib.parse.quote(self.config)

    def search(self, page=None):
        url = self.url

        if page:
            url = url + ("&" if "?" in self.url else "?") + "page=" + str(page)

        logger.info(lambda: "Performing wallhaven search: url=%s" % url)

        soup = Util.html_soup(url)

        result_count = None
        try:
            result_count = int(
                soup.find("header", {"class": "listing-header"})
                .find("h1")
                .text.split()[0]
                .replace(",", "")
            )
        except:
            pass

        return soup, result_count

    @staticmethod
    def validate(location):
        logger.info(lambda: "Validating Wallhaven location " + location)
        try:
            s, count = WallhavenDownloader(None, location).search()
            wall = s.find("figure", {"class": "thumb"})
            if not wall:
                return False
            link = wall.find("a", {"class": "preview"})
            return link is not None
        except Exception:
            logger.exception(lambda: "Error while validating wallhaven search")
            return False

    def download_queue_item(self, queue_item):
        wallpaper_url = queue_item
        logger.info(lambda: "Wallpaper URL: " + wallpaper_url)

        s = Util.html_soup(wallpaper_url)
        src_url = s.find("img", id="wallpaper")["src"]
        logger.info(lambda: "Image src URL: " + src_url)

        extra_metadata = {}
        try:
            extra_metadata["keywords"] = [
                el.text.strip() for el in s.find_all("a", {"class": "tagname"})
            ]
        except:
            pass

        try:
            purity = s.find("div", "sidebar-content").find("label", "purity").text.lower()
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

        thumbs = s.find_all("figure", {"class": "thumb"})
        for thumb in thumbs:
            try:
                p = list(map(int, thumb.find("span", {"class": "wall-res"}).contents[0].split("x")))
                width = p[0]
                height = p[1]
                if self.is_size_inadequate(width, height):
                    continue
            except Exception:
                # missing or unparseable resolution - consider ok
                pass

            try:
                link = thumb.find("a", {"class": "preview"})["href"]
                if self.is_in_banned(link):
                    continue
                queue.append(link)
            except Exception:
                logger.debug(lambda: "Missing link for thumbnail")

        random.shuffle(queue)

        if not_random and len(queue) >= 20:
            queue = queue[: len(queue) // 2]
            # only use randomly half the images from the page -
            # if we ever hit that same page again, we'll still have what to download

        return queue
