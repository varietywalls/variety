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
import base64

import urllib
from bs4 import BeautifulSoup
import random

import logging
import time
from variety import Downloader
from variety.Util import Util

logger = logging.getLogger('variety')

random.seed()

class WallbaseDownloader(Downloader.Downloader):
    last_download_time = 0

    def __init__(self, parent, location):
        super(WallbaseDownloader, self).__init__(parent, "Wallbase.cc", location)
        self.parse_location()
        self.last_fill_time = 0
        self.queue = []

    def convert_to_filename(self, url):
        return "wallbase_" + super(WallbaseDownloader, self).convert_to_filename(url)

    def parse_location(self):
        if self.location.startswith(('http://', 'https://')):
            # location is an URL, use it
            self.url = self.location
            return

        elif 'type:' not in self.location:
            # interpret location as keywords
            self.url = "http://wallbase.cc/search?q=%s&section=wallpapers&order_mode=desc&order=favs&purity=100&board=213" % urllib.quote(self.location)
            return

        # else the lcoation is in the old format, parse it:
        s = self.location.split(';')
        params = {}
        for x in s:
            if len(x) and x.find(':') > 0:
                k, v = x.split(':')
                params[k.lower()] = v

        prefer_favs = params.get("order") == "favs"

        m = {"thpp": 60}

        if "nsfw" in params:
            m["purity"] = params["nsfw"]

        if "board" in params:
            m["board"] = params["board"]

        self.url = "http://wallbase.cc/search"
        if params["type"] == "text":
            m["q"] = params["query"]
        elif params["type"] == "color":
            m["color"] = params["color"]

        if prefer_favs:
            m["order"] = "favs"
        else:
            m["order"] = "random"

        data = urllib.urlencode(m)
        self.url = self.url + "?" + data

    def search(self, start_from=None):
        url = self.url + ("&" if "?" in self.url else "?") + "thpp=60"

        if self.parent and self.parent.options.min_size_enabled and not "res=" in url:
            url += "&res_opt=gteq&res=%dx%d" % (max(100, self.parent.min_width), max(100, self.parent.min_height))

        if start_from:
            url = url.replace('?', '/index/%d?' % start_from, 1)

        logger.info("Performing wallbase search: url=%s" % url)
        return Util.html_soup(url)

    @staticmethod
    def validate(location):
        logger.info("Validating Wallbase location " + location)
        try:
            s = WallbaseDownloader(None, location).search()
            wall = s.find("div", "thumbnail")
            if not wall:
                return False
            link = wall.find("img", "file")
            return link is not None
        except Exception:
            logger.exception("Error while validating wallbase search")
            return False

    def download_one(self):
        min_download_interval, min_fill_queue_interval = self.parse_server_options("wallbase", 0, 0)

        if time.time() - WallbaseDownloader.last_download_time < min_download_interval:
            logger.info("Minimal interval between Wallbase downloads is %d, skip this attempt" % min_download_interval)
            return None

        logger.info("Downloading an image from Wallbase.cc, " + self.location)
        logger.info("Queue size: %d" % len(self.queue))

        if not self.queue:
            if time.time() - self.last_fill_time < min_fill_queue_interval:
                logger.info("Wallbase queue empty, but minimal interval between fill attempts is %d, "
                            "will try again later" % min_fill_queue_interval)
                return None

            self.fill_queue()

        if not self.queue:
            logger.info("Wallbase queue still empty after fill request")
            return None

        WallbaseDownloader.last_download_time = time.time()

        wallpaper_url = self.queue.pop()
        logger.info("Wallpaper URL: " + wallpaper_url)

        s = Util.html_soup(wallpaper_url)
        src_url = s.find('img', 'wall')['src']
        logger.info("Image src URL: " + src_url)

        return self.save_locally(wallpaper_url, src_url)

    def fill_queue(self):
        self.last_fill_time = time.time()

        logger.info("Filling wallbase queue: " + self.location)

        start_from = None
        not_random = not "order=random" in self.url
        if not_random:
            start_from = random.randint(0, 300 - 60)
            s = self.search(start_from=start_from)
        else:
            s = self.search()

        thumbs = s.find_all('div', 'thumbnail')

        if start_from and not thumbs:  # oops, no results - probably too few matches, use the first page of results
            logger.info("Nothing found when using start index %d, rerun with no start index" % start_from)
            s = self.search()
            thumbs = s.find_all('div', 'thumbnail')

        for thumb in thumbs:
            try:
                p = map(int, thumb.find('span', 'reso').contents[0].split('x'))
                width = p[0]
                height = p[1]
                if self.parent and not self.parent.size_ok(width, height):
                    continue
            except Exception:
                # missing or unparseable resolution - consider ok
                pass

            try:
                link = thumb.find('a', target='_blank')["href"]
                if self.parent and link in self.parent.banned:
                    continue
                self.queue.append(link)
            except Exception:
                logger.debug("Missing link for thumbnail")

        random.shuffle(self.queue)

        if not_random and len(self.queue) >= 20:
            self.queue = self.queue[:len(self.queue)//2]
            # only use randomly half the images from the page -
            # if we ever hit that same page again, we'll still have what to download

        logger.info("Wallbase queue populated with %d URLs" % len(self.queue))
