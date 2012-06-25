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
        self.queue = []

    def download_one(self):
        logger.info("Downloading an image from wallpapers.net, " + self.category_url)

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
            page_url = self.host + h[:h.index("/page/") + 6] + str(page)

            logger.info("Page URL: " + page_url)
            content = urllib2.urlopen(page_url).read()
            s = BeautifulSoup(content)
        else:
            logger.info("Single page in category")

        walls = [self.host + x.a['href'] for x in s.find_all('div', 'thumb')]

        self.queue.extend(walls)

    def save_locally(self, wallpaper_url, src_url):
        name = src_url[src_url.rindex('/') + 1:]
        logger.info("Name: " + name)

        local_filename = os.path.join(self.target_dir, name)
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

