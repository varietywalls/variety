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
import json
import os
import random
import logging
import requests

import time

from variety import Downloader
from variety.Util import Util

logger = logging.getLogger('variety')

random.seed()


class UnsplashDownloader(Downloader.Downloader):
    last_download_time = 0
    rate_limiting_started_time = 0

    CLIENT_ID = '072e5048dfcb73a8d9ad59fcf402471518ff8df725df462b0c4fa665f466515a'

    def __init__(self, parent):
        super(UnsplashDownloader, self).__init__(parent, "unsplash", "Unsplash.com", "https://unsplash.com")
        self.last_fill_time = 0
        self.queue = []

    def convert_to_filename(self, url):
        return "Unsplash"

    def download_one(self):
        min_download_interval, min_fill_queue_interval = self.parse_server_options("unsplash", 0, 0)

        if time.time() - UnsplashDownloader.last_download_time < min_download_interval:
            logger.info(lambda: "Minimal interval between Unsplash downloads is %d, skip this attempt" % min_download_interval)
            return None

        logger.info(lambda: "Downloading an image from Unsplash")
        logger.info(lambda: "Queue size: %d" % len(self.queue))

        if not self.queue:
            if time.time() - UnsplashDownloader.rate_limiting_started_time < 3600:
                logger.info(lambda: "Unsplash queue empty, but rate limit reached, will try again later")
                return None

            if time.time() - self.last_fill_time < min_fill_queue_interval:
                logger.info(lambda: "Unsplash queue empty, but minimal interval between fill attempts is %d, "
                            "will try again later" % min_fill_queue_interval)
                return None

            self.last_fill_time = time.time()
            self.fill_queue()

        if not self.queue:
            logger.info(lambda: "Unsplash queue still empty after fill request")
            return None

        UnsplashDownloader.last_download_time = time.time()

        origin_url, image_url, extra_metadata, filename = self.queue.pop()
        return self.save_locally(origin_url, image_url, extra_metadata=extra_metadata, local_filename=filename)

    def fill_queue(self):
        page = random.randint(1, 250)
        url = 'https://api.unsplash.com/photos/?page=%d&per_page=30&client_id=%s' % (page, UnsplashDownloader.CLIENT_ID)
        logger.info(lambda: "Filling Unsplash queue from " + url)

        r = requests.get(url, allow_redirects=True)
        r.raise_for_status()
        if int(r.headers.get('X-Ratelimit-Remaining', 1000000)) < 100:
            UnsplashDownloader.rate_limiting_started_time = time.time()

        for item in r.json():
            try:
                width = item['width']
                height = item['height']
                if self.parent and not self.parent.size_ok(width, height):
                    continue

                image_url = item['links']['download']
                origin_url = item['links']['html']

                filename = os.path.join(self.target_folder, Util.sanitize_filename(image_url.split('/')[-2] + '.jpg'))
                extra_metadata = {
                    'sourceType': 'unsplash',
                    'sfwRating': 100,
                    'author': item['user']['name'],
                    'authorURL': item['user']['links']['html'],
                    'keywords': [cat['title'].lower().strip() for cat in item['categories']]
                }

                self.queue.append((origin_url, image_url, extra_metadata, filename))
            except:
                logger.exception(lambda: "Could not process an item from Unsplash")
                raise

        random.shuffle(self.queue)
        logger.info(lambda: "Unsplash populated with %d URLs" % len(self.queue))