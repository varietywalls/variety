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

import os
import string
import urllib2
from bs4 import BeautifulSoup
import random
import re

import logging

logger = logging.getLogger('variety')

random.seed()

WN_HOST = "http://wallpapers.net"

class WallpapersNetScraper():
    def __init__(self, category_url, download_folder):
        self.category_url = category_url

        self.target_folder = os.path.join(download_folder, WallpapersNetScraper.convert_to_filename(category_url))
        self.queue = []

    @staticmethod
    def convert_to_filename(url):
        if url.startswith(WN_HOST):
            url = url[len(WN_HOST) + 1:]
        valid_chars = "-_%s%s" % (string.ascii_letters, string.digits)
        return ''.join(c if c in valid_chars else '_' for c in url)

    def download_one(self):
        logger.info("Downloading an image from wallpapers.net, " + self.category_url)

        if not self.queue:
            self.fill_queue()

        wallpaper_url = self.queue.pop()
        logger.info("Wallpaper URL: " + wallpaper_url)

        content = urllib2.urlopen(wallpaper_url).read()
        s = BeautifulSoup(content)
        img_url = WN_HOST + s.find('a', text=re.compile("Original format"))['href']
        logger.info("Image page URL: " + img_url)

        content = urllib2.urlopen(img_url).read()
        s = BeautifulSoup(content)
        src_url = s.img['src']
        logger.info("Image src URL: " + src_url)

        self.save_locally(wallpaper_url, src_url)

    def fill_queue(self):
        logger.info("Category URL: " + self.category_url)
        content = urllib2.urlopen(self.category_url).read()
        s = BeautifulSoup(content)
        mp = 0
        urls = [url['href'] for x in s.find_all('div', 'pagination') for url in x.find_all('a') if
                url['href'].index('/page/') > 0]

        if urls:
            for h in urls:
                page = h[h.index("/page/") + 6:]
                mp = max(mp, int(page))

            # special case the top wallpapers - limit to the best 200 pages
            if self.category_url.find("top_wallpapers"):
                mp = min(mp, 200)

            page = random.randint(0, mp)
            h = urls[0]
            page_url = WN_HOST + h[:h.index("/page/") + 6] + str(page)

            logger.info("Page URL: " + page_url)
            content = urllib2.urlopen(page_url).read()
            s = BeautifulSoup(content)
        else:
            logger.info("Single page in category")

        walls = [WN_HOST + x.a['href'] for x in s.find_all('div', 'thumb')]

        self.queue.extend(walls)

    def save_locally(self, wallpaper_url, src_url):
        name = src_url[src_url.rindex('/') + 1:]
        logger.info("Name: " + name)

        try:
            os.makedirs(self.target_folder)
        except Exception:
            pass

        local_filename = os.path.join(self.target_folder, name)
        if os.path.exists(local_filename):
            logger.info("File already exists, skip downloading")
            return

        u = urllib2.urlopen(src_url)
        data = u.read()
        localFile = open(local_filename, 'wb')
        localFile.write(data)
        localFile.close()

        localFile = open(local_filename + ".txt", 'w')
        localFile.write("INFO:\nDownloaded from Wallpapers.net\n" + wallpaper_url)
        localFile.close()

        logger.info("Download complete")
