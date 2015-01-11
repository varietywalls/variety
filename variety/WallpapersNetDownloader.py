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
from lxml import etree
import StringIO
from variety import Downloader
from variety.Util import Util

logger = logging.getLogger('variety')

random.seed()

class WallpapersNetDownloader(Downloader.Downloader):
    last_download_time = 0

    def __init__(self, parent, category_url):
        super(WallpapersNetDownloader, self).__init__(parent, "wn", "Wallpapers.net", category_url)
        self.host = "http://wallpapers.net/"
        self.last_fill_time = 0
        self.queue = []

    @staticmethod
    def fetch_and_parse(url):
        html = Util.fetch(url)
        return etree.parse(StringIO.StringIO(html), etree.HTMLParser())

    @staticmethod
    def validate(url):
        logger.info(lambda: "Validating WN url " + url)
        try:
            if not url.startswith("http://"):
                url = "http://" + url
            if not url.lower().startswith("http://www.wallpapers.net") and not url.lower().startswith("http://wallpapers.net"):
                return False

            tree = WallpapersNetDownloader.fetch_and_parse(url)
            walls = list(tree.findall('//**/div[@class="screen"]/div[@class="title"]/a'))
            return len(walls) > 0
        except Exception:
            logger.exception(lambda: "Error while validating URL, proabably bad URL")
            return False

    def download_one(self):
        min_download_interval, min_fill_queue_interval = self.parse_server_options("wallpapers.net", 0, 0)

        if time.time() - WallpapersNetDownloader.last_download_time < min_download_interval:
            logger.info(lambda: "Minimal interval between Wallpapers.net downloads is %d, skip this attempt" %
                        min_download_interval)
            return None

        logger.info(lambda: "Downloading an image from Wallpapers.net, " + self.location)
        logger.info(lambda: "Queue size: %d" % len(self.queue))

        if not self.queue:
            if time.time() - self.last_fill_time < min_fill_queue_interval:
                logger.info(lambda: "Wallpapers.net queue empty, but minimal interval between fill attempts is %d, "
                            "will try again later" % min_fill_queue_interval)
                return None

            self.fill_queue()

        if not self.queue:
            logger.info(lambda: "WN Queue still empty after fill request - probably wrong URL?")
            return None

        WallpapersNetDownloader.last_download_time = time.time()

        wallpaper_url = self.queue.pop()
        logger.info(lambda: "Wallpaper URL: " + wallpaper_url)

        tree = WallpapersNetDownloader.fetch_and_parse(wallpaper_url)
        resolution_links = [a.get("href") for a in tree.findall('**/table/tr/td/a') if a.get('href').endswith(('.jpg', '.jpeg'))]
        max_res_link = max(resolution_links, key=lambda a: re.search('(\d+)x(\d+)\.', a).group(1))
        src_url = self.host + max_res_link
        logger.info(lambda: "Image src URL: " + src_url)

        extra_metadata = {}
        try:
            extra_metadata['headline'] = tree.findall('//h1')[0].text.replace('HD Wallpaper', '')
        except:
            pass
        try:
            extra_metadata['keywords'] = [x[1:].lower() for x in map(
                lambda a: str(a.text), tree.findall('//div[@class="right"]//table//a')) if x.startswith('#')]
        except:
            pass

        return self.save_locally(wallpaper_url, src_url, extra_metadata=extra_metadata)

    def fill_queue(self):
        self.last_fill_time = time.time()

        logger.info(lambda: "Category URL: " + self.location)
        tree = WallpapersNetDownloader.fetch_and_parse(self.location)
        mp = 0
        urls = [url.get('href') for url in tree.findall('**/div[@class="pagination"]/a') if url.get('href').find('_p') > 0]

        if urls:
            for h in urls:
                page = (re.search(r'_p(\d+)$', h)).group(1)
                mp = max(mp, int(page))

            page = random.randint(1, mp)
            h = urls[0]
            page_url = self.host + re.sub(r'_p\d+$', '_p%d' % page, h)

            logger.info(lambda: "Page URL: " + page_url)
            tree = WallpapersNetDownloader.fetch_and_parse(page_url)
        else:
            logger.info(lambda: "Single page in category")

        walls = [self.host + a.get('href') for a in tree.findall('//**/div[@class="screen"]/div[@class="title"]/a')]
        walls = [x for x in walls if x not in self.parent.banned]

        self.queue.extend(walls)

        random.shuffle(self.queue)
        if len(self.queue) >= 8:
            self.queue = self.queue[:len(self.queue)//2]
            # only use randomly half the images from the page -
            # if we ever hit that same page again, we'll still have what to download

        logger.info(lambda: "WN queue populated with %d URLs" % len(self.queue))