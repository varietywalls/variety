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
import urllib
import random

import logging
import time
from variety import Downloader
from variety.Util import Util

logger = logging.getLogger('variety')

random.seed()

class WallhavenDownloader(Downloader.Downloader):
    last_download_time = 0

    def __init__(self, parent, location):
        super(WallhavenDownloader, self).__init__(parent, "Wallhaven.cc", location)
        self.parse_location()
        self.last_fill_time = 0
        self.queue = []

    def convert_to_filename(self, url):
        return "wallhaven_" + super(WallhavenDownloader, self).convert_to_filename(url)

    def parse_location(self):
        if self.location.startswith(('http://', 'https://')):
            # location is an URL, use it
            self.url = self.location
        else:
            # interpret location as keywords
            self.url = "http://alpha.wallhaven.cc/search?q=%s&categories=111&purity=100&sorting=favorites&order=desc" % urllib.quote(self.location)

    def search(self, page=None):
        url = self.url

        if page:
            url = url + ("&" if "?" in self.url else "?") + "page=" + str(page)

        logger.info("Performing wallhaven search: url=%s" % url)

        soup = Util.html_soup(url)

        result_count = None
        try:
            result_count = int(soup.find('header', {'class': 'listing-header'}).find('h1').text.split()[0])
        except:
            pass

        return soup, result_count

    @staticmethod
    def validate(location):
        logger.info("Validating Wallhaven location " + location)
        try:
            s, count = WallhavenDownloader(None, location).search()
            wall = s.find("figure", {"class": "thumb"})
            if not wall:
                return False
            link = wall.find("a", {"class": "preview"})
            return link is not None
        except Exception:
            logger.exception("Error while validating wallhaven search")
            return False

    def download_one(self):
        min_download_interval, min_fill_queue_interval = self.parse_server_options("wallhaven", 0, 0)

        if time.time() - WallhavenDownloader.last_download_time < min_download_interval:
            logger.info("Minimal interval between Wallhaven downloads is %d, skip this attempt" % min_download_interval)
            return None

        logger.info("Downloading an image from Wallhaven.cc, " + self.location)
        logger.info("Queue size: %d" % len(self.queue))

        if not self.queue:
            if time.time() - self.last_fill_time < min_fill_queue_interval:
                logger.info("Wallhaven queue empty, but minimal interval between fill attempts is %d, "
                            "will try again later" % min_fill_queue_interval)
                return None

            self.fill_queue()

        if not self.queue:
            logger.info("Wallhaven queue still empty after fill request")
            return None

        WallhavenDownloader.last_download_time = time.time()

        wallpaper_url = self.queue.pop()
        logger.info("Wallpaper URL: " + wallpaper_url)

        s = Util.html_soup(wallpaper_url)
        src_url = s.find('img', id='wallpaper')['src']
        logger.info("Image src URL: " + src_url)

        extra_metadata = {}
        try:
            extra_metadata['keywords'] = [el.text.strip() for el in s.find_all('a', {'class':'tagname'})]
        except:
            pass

        return self.save_locally(wallpaper_url, src_url, extra_metadata=extra_metadata)

    def fill_queue(self):
        self.last_fill_time = time.time()

        logger.info("Filling wallhaven queue: " + self.location)

        not_random = not "sorting=random" in self.url
        if not_random:
            s, count = self.search()
            if not count:
                count = 300
            pages = min(count, 300) / 24 + 1
            page = random.randint(1, pages)
            logger.info('%s wallpapers in result, using page %s' % (count, page))
            s, count = self.search(page=page)
        else:
            s, count = self.search()

        thumbs = s.find_all('figure', {'class': 'thumb'})
        for thumb in thumbs:
            try:
                p = map(int, thumb.find('span', {'class': 'wall-res'}).contents[0].split('x'))
                width = p[0]
                height = p[1]
                if self.parent and not self.parent.size_ok(width, height):
                    continue
            except Exception:
                # missing or unparseable resolution - consider ok
                pass

            try:
                link = thumb.find('a', {'class': 'preview'})["href"]
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

        logger.info("Wallhaven queue populated with %d URLs" % len(self.queue))
