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
from datetime import datetime
import os

import random
import urlparse

import logging
import re
from variety import Downloader
from variety.Util import Util
import requests

logger = logging.getLogger('variety')

random.seed()


class UnsplashDownloader(Downloader.Downloader):
    def __init__(self, parent):
        super(UnsplashDownloader, self).__init__(parent, "unsplash", "Unsplash.com", "https://unsplash.com")
        self.queue = []

    def convert_to_filename(self, url):
        return "Unsplash"

    def download_one(self):
        logger.info(lambda: "Downloading an image from Unsplash")
        logger.info(lambda: "Queue size: %d" % len(self.queue))

        if not self.queue:
            self.fill_queue()
        if not self.queue:
            logger.info(lambda: "Unsplash queue empty after fill")
            return None

        origin_url, image_url, extra_metadata, filename = self.queue.pop()
        return self.save_locally(origin_url, image_url, extra_metadata=extra_metadata, local_filename=filename)

    def fill_queue(self):
        page = random.randint(1, 400)
        url = 'https://unsplash.com/filter?page=' + str(page)
        logger.info(lambda: "Filling Unsplash queue from " + url)

        s = Util.html_soup(url)

        for item in s.find_all('div', 'photo-description'):
            try:
                image_url = self.location + item.find_all('a')[0]['href']
                origin_url = image_url.replace('/download', '')
                filename = os.path.join(self.target_folder, Util.sanitize_filename(image_url.split('/')[-2] + '.jpg'))
                extra_metadata = {
                    'sourceType': 'unsplash',
                    'sfwRating': 100,
                    'author': item.find_all('a')[1].contents[0],
                    'authorURL': self.location + item.find_all('a')[1]['href'],
                }

                redirect_url = requests.head(image_url).headers['Location']
                final_image_url = redirect_url.replace('https://', 'http://')
                # disable https for this specific call - it fails on 12.04 with an SSL related error:
                # URLError: <urlopen error [Errno 1] _ssl.c:504: error:14077410:SSL routines:SSL23_GET_SERVER_HELLO:sslv3 alert handshake failure>.
                self.queue.append((origin_url, final_image_url, extra_metadata, filename))
            except:
                logger.exception(lambda: "Could not process an item from Unsplash")
                raise

        random.shuffle(self.queue)
        logger.info(lambda: "Unsplash populated with %d URLs" % len(self.queue))