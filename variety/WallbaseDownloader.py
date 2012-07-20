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
        self.host = "http://wallbase.cc"
        self.parse_location()
        self.queue = []

    def convert_to_filename(self, url):
        return "wallbase_" + super(WallbaseDownloader, self).convert_to_filename(url)

    def parse_location(self):
        s = self.location.split(';')
        self.params = {}
        for x in s:
            if len(x) and x.find(':') > 0:
                k, v = x.split(':')
                if k.lower() in ["query", "board", "nsfw"]:
                    self.params[k.lower()] = v

    @staticmethod
    def fetch(url):
        content = urllib2.urlopen(url, timeout=20).read()
        return BeautifulSoup(content)

    def search(self):
        m = {"orderby" : "random", "thpp" : 60}
        m.update(self.params)
        data = urllib.urlencode(m)
        content = urllib2.urlopen("http://wallbase.cc/search", data=data, timeout=20).read()
        return BeautifulSoup(content)

    @staticmethod
    def validate(query):
        query = query.strip()
        if not len(query):
            return True

        try:
            s = WallbaseDownloader(None, "query:%s" % query).search()
            wall = s.find("div", "thumb")
            if not wall:
                return False
            link = wall.find("a", "thlink")
            return link is not None
        except Exception:
            logger.exception("Error while validating wallbase search")
            return False

    def download_one(self):
        logger.info("Downloading an image from wallbase.cc, " + self.location)

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

        for thumb in s.find_all('div', 'thumb'):
            try:
                p = map(int, thumb.find('span','res').contents[0].split('x'))
                width = p[0]
                height = p[1]
                if self.parent and not self.parent.size_ok(width, height):
                    continue
            except Exception:
                # missing or unparseable resolution - consider ok
                logger.debug("Missing or unparseable resolution, considering OK")
                pass

            try:
                link = thumb.find('a', 'thlink')["href"]
                if self.parent and link in self.parent.banned:
                    continue
                self.queue.append(link)
            except Exception:
                logger.debug("Missing link for thumbnail")

        random.shuffle(self.queue)
        logger.info("Wallbase queue populated with %d URLs" % len(self.queue))
