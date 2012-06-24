#!/usr/bin/python

import os
import urllib2
from bs4 import BeautifulSoup
import random
import re

import logging

logger = logging.getLogger('variety')

random.seed()

class WallpapersNetScraper():
    def __init__(self, category_url, target_dir):
        self.host = "http://wallpapers.net"
        self.category_url = category_url
        self.target_dir = target_dir

    def download_one(self):
        logger.info('Downloading an image from wallpapers.net')

        content = urllib2.urlopen(self.category_url).read()
        s = BeautifulSoup(content)
        mp = 0
        urls = [url['href'] for x in s.find_all('div', 'pagination') for url in x.find_all('a') if url['href'].index('/page/') > 0]
        for h in urls:
            page = h[h.index("/page/") + 6:]
            mp = max(mp, int(page))

        # special case the top wallpapers - limit to the best 200 pages
        if self.category_url.find("top_wallpapers"):
            mp = min(mp, 200)

        page = random.randint(0, mp)
        h = urls[0]
        page_url = self.host + h[:h.index("/page/") + 6] + str(page)
        logger.info("Page " + page_url)

        content = urllib2.urlopen(page_url).read()
        s = BeautifulSoup(content)
        walls = [x.a['href'] for x in s.find_all('div', 'thumb')]

        wallpaper_url = self.host + walls[random.randint(0, len(walls) - 1)]
        logger.info("Wallpaper: " + wallpaper_url)

        content = urllib2.urlopen(wallpaper_url).read()
        s = BeautifulSoup(content)
        img_url = self.host + s.find('a', text=re.compile("Original format"))['href']
        logger.info("Image: " + img_url)

        content = urllib2.urlopen(img_url).read()
        s = BeautifulSoup(content)
        src_url = s.img['src']
        logger.info("Image src " + src_url)

        name = src_url[src_url.rindex('/') + 1:]
        logger.info("Name " + name)

        u = urllib2.urlopen(src_url)
        localFile = open(os.path.join(self.target_dir, name), 'wb')
        localFile.write(u.read())
        localFile.close()

        localFile = open(os.path.join(self.target_dir, name + ".txt"), 'w')
        localFile.write("INFO:\nDownloaded from Wallpapers.net\n" + wallpaper_url)
        localFile.close()
