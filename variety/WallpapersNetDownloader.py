#!/usr/bin/python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2012 Peter Levi <peterlevi@peterlevi.com>
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

import urllib2
from bs4 import BeautifulSoup
import random
import re

import logging
from variety import Downloader

logger = logging.getLogger('variety')

random.seed()

class WallpapersNetDownloader(Downloader.Downloader):
    def __init__(self, category_url, download_folder):
        super(WallpapersNetDownloader, self).__init__("Wallpapers.net", category_url, download_folder)
        self.host = "http://wallpapers.net"
        self.queue = []

    def download_one(self):
        logger.info("Downloading an image from wallpapers.net, " + self.location)

        if not self.queue:
            self.fill_queue()

        wallpaper_url = self.queue.pop()
        logger.info("Wallpaper URL: " + wallpaper_url)

        content = urllib2.urlopen(wallpaper_url).read()
        s = BeautifulSoup(content)
        img_url = self.host + s.find('a', text=re.compile("Original format"))['href']
        logger.info("Image page URL: " + img_url)

        content = urllib2.urlopen(img_url).read()
        s = BeautifulSoup(content)
        src_url = s.img['src']
        logger.info("Image src URL: " + src_url)

        self.save_locally(wallpaper_url, src_url)

    def fill_queue(self):
        logger.info("Category URL: " + self.location)
        content = urllib2.urlopen(self.location).read()
        s = BeautifulSoup(content)
        mp = 0
        urls = [url['href'] for x in s.find_all('div', 'pagination') for url in x.find_all('a') if
                url['href'].index('/page/') > 0]

        if urls:
            for h in urls:
                page = h[h.index("/page/") + 6:]
                mp = max(mp, int(page))

            # special case the top wallpapers - limit to the best 200 pages
            if self.location.find("top_wallpapers"):
                mp = min(mp, 200)

            page = random.randint(0, mp)
            h = urls[0]
            page_url = self.host + h[:h.index("/page/") + 6] + str(page)

            logger.info("Page URL: " + page_url)
            content = urllib2.urlopen(page_url).read()
            s = BeautifulSoup(content)
        else:
            logger.info("Single page in category")

        walls = [self.host + x.a['href'] for x in s.find_all('div', 'thumb')]

        self.queue.extend(walls)
        logger.info("WN queue populated with %d URLs" % len(self.queue))