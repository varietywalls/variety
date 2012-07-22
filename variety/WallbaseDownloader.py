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

import urllib
import urllib2
from bs4 import BeautifulSoup
import random

import logging
from variety import Downloader

logger = logging.getLogger('variety')

random.seed()

class WallbaseDownloader(Downloader.Downloader):
    def __init__(self, parent, location):
        super(WallbaseDownloader, self).__init__(parent, "Wallbase.cc", location)
        self.parse_location()
        self.type = self.params["type"]
        self.prefer_favs = "order" in self.params and self.params["order"] == "favs"
        self.queue = []

    def convert_to_filename(self, url):
        return "wallbase_" + super(WallbaseDownloader, self).convert_to_filename(url)

    def parse_location(self):
        s = self.location.split(';')
        self.params = {}
        for x in s:
            if len(x) and x.find(':') > 0:
                k, v = x.split(':')
                self.params[k.lower()] = v

    @staticmethod
    def fetch(url):
        content = urllib2.urlopen(url, timeout=20).read()
        return BeautifulSoup(content)

    def search(self, start_from = None, thpp = 60):
        m = {"thpp": thpp}

        if self.parent and self.parent.options.min_size_enabled:
            m["res_opt"] = "gteq"
            m["res"] = "%dx%d" % (max(100, self.parent.min_width), max(100, self.parent.min_height))

        if "nsfw" in self.params:
            m["nsfw"] = self.params["nsfw"]

        if "board" in self.params:
            m["board"] = self.params["board"]

        if self.type == "text":
            url = "http://wallbase.cc/search"
            m["query"] = self.params["query"]
        elif self.type == "color":
            url = "http://wallbase.cc/search/color/" + self.params["color"]
        else:
            url = "http://wallbase.cc/search"

        if start_from:
            url += "/%d" % start_from

        if self.prefer_favs:
            m["orderby"] = "favs"
        else:
            m["orderby"] = "random"

        data = urllib.urlencode(m)

        logger.info("Performing wallbase search: url=%s, data=%s" % (url, data))

        content = urllib2.urlopen(url, data=data, timeout=20).read()
        return BeautifulSoup(content)

    @staticmethod
    def validate(location):
        logger.info("Validating Wallbase location " + location)
        try:
            s = WallbaseDownloader(None, location).search()
            wall = s.find("div", "thumb")
            if not wall:
                return False
            link = wall.find("a", "thlink")
            return link is not None
        except Exception:
            logger.exception("Error while validating wallbase search")
            return False

    def download_one(self):
        logger.info("Downloading an image from Wallbase.cc, " + self.location)
        logger.info("Queue size: %d" % len(self.queue))

        if not self.queue:
            self.fill_queue()
        if not self.queue:
            logger.info("Wallbase queue still empty after fill request")
            return None

        wallpaper_url = self.queue.pop()
        logger.info("Wallpaper URL: " + wallpaper_url)

        s = self.fetch(wallpaper_url)
        src_url = s.find('div', id='bigwall').find('img')['src']
        logger.info("Image src URL: " + src_url)

        return self.save_locally(wallpaper_url, src_url)

    def fill_queue(self):
        logger.info("Filling wallbase queue: " + self.location)
        s = self.search()

        limit = 10^9
        if self.prefer_favs:
            total_count = int(s.find("div", "imgshow").contents[0].replace(",", ""))
            favs_count = int(self.params["favs_count"])
            logger.info("Preferring the most liked %d images of total %d" % (favs_count, total_count))
            limit = min(total_count, favs_count)
            start_from = random.randint(0, max(0, limit - 60))
            s = self.search(start_from=start_from)

        for thumb in s.find_all('div', 'thumb'):
            try:
                p = map(int, thumb.find('span','res').contents[0].split('x'))
                width = p[0]
                height = p[1]
                if self.parent and not self.parent.size_ok(width, height):
                    continue
            except Exception:
                # missing or unparseable resolution - consider ok
                pass

            try:
                link = thumb.find('a', 'thlink')["href"]
                if self.parent and link in self.parent.banned:
                    continue
                self.queue.append(link)
            except Exception:
                logger.debug("Missing link for thumbnail")

        if self.prefer_favs and len(self.queue) > limit:
            self.queue = self.queue[:limit]

        random.shuffle(self.queue)

        if self.prefer_favs and len(self.queue) >= 20:
            self.queue = self.queue[:len(self.queue)//2]
            # only use randomly half the images from the page -
            # if we ever hit that same page again, we'll still have what to download

        logger.info("Wallbase queue populated with %d URLs" % len(self.queue))
