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

import random
import re

import logging
import time
from variety import Downloader
from variety.Util import Util

logger = logging.getLogger('variety')

random.seed()

class WallpapersNetDownloader(Downloader.Downloader):
    last_download_time = 0

    def __init__(self, parent, category_url):
        super(WallpapersNetDownloader, self).__init__(parent, "Wallpapers.net", category_url)
        self.host = "http://wallpapers.net"
        self.last_fill_time = 0
        self.queue = []

    @staticmethod
    def validate(url):
        logger.info("Validating WN url " + url)
        try:
            if not url.startswith("http://"):
                url = "http://" + url
            if not url.lower().startswith("http://www.wallpapers.net") and not url.lower().startswith("http://wallpapers.net"):
                return False

            s = Util.html_soup(url)
            walls = [wall.find("a") for wall in s.findAll("div", "wall")]
            return len(walls) > 0
        except Exception:
            logger.exception("Error while validating URL, proabably bad URL")
            return False

    def download_one(self):
        min_download_interval, min_fill_queue_interval = self.parse_server_options("wallpapers.net", 0, 0)

        if time.time() - WallpapersNetDownloader.last_download_time < min_download_interval:
            logger.info("Minimal interval between Wallpapers.net downloads is %d, skip this attempt" %
                        min_download_interval)
            return None

        logger.info("Downloading an image from Wallpapers.net, " + self.location)
        logger.info("Queue size: %d" % len(self.queue))

        if not self.queue:
            if time.time() - self.last_fill_time < min_fill_queue_interval:
                logger.info("Wallpapers.net queue empty, but minimal interval between fill attempts is %d, "
                            "will try again later" % min_fill_queue_interval)
                return None

            self.fill_queue()

        if not self.queue:
            logger.info("WN Queue still empty after fill request - probably wrong URL?")
            return None

        WallpapersNetDownloader.last_download_time = time.time()

        wallpaper_url = self.queue.pop()
        logger.info("Wallpaper URL: " + wallpaper_url)

        s = Util.html_soup(wallpaper_url)
        resolution_links = s.find('div', 'resolutionsList').find_all('a')
        max_res_link = max(resolution_links, key=lambda a: int(a['title'].split()[0]))
        img_url = self.host + max_res_link['href']
        logger.info("Image page URL: " + img_url)

        s = Util.html_soup(img_url)
        src_url = s.img['src']
        logger.info("Image src URL: " + src_url)

        return self.save_locally(wallpaper_url, src_url)

    def fill_queue(self):
        self.last_fill_time = time.time()

        logger.info("Category URL: " + self.location)
        s = Util.html_soup(self.location)
        mp = 0
        urls = [url['href'] for x in s.find_all('div', 'pagination') for url in x.find_all('a') if
                url['href'].index('/page/') > 0]

        if urls:
            for h in urls:
                page = (re.search(r'/page/(\d+)', h)).group(1)
                mp = max(mp, int(page))

            # special case the top wallpapers - limit to the best 200 pages
            if "top_wallpapers" in self.location:
                mp = min(mp, 200)

            page = random.randint(0, mp)
            h = urls[0]
            page_url = self.host + re.sub(r'/page/\d+', '/page/%d' % page, h)

            logger.info("Page URL: " + page_url)
            s = Util.html_soup(page_url)
        else:
            logger.info("Single page in category")

        walls = [self.host + x.a['href'] for x in s.find_all('div', 'wall')]
        walls = [x for x in walls if x not in self.parent.banned]

        self.queue.extend(walls)

        random.shuffle(self.queue)
        if len(self.queue) >= 8:
            self.queue = self.queue[:len(self.queue)//2]
            # only use randomly half the images from the page -
            # if we ever hit that same page again, we'll still have what to download

        logger.info("WN queue populated with %d URLs" % len(self.queue))