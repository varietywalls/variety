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
import urlparse

import logging
import re
from variety import Downloader
from variety.Util import Util

logger = logging.getLogger('variety')

random.seed()


class RedditDownloader(Downloader.Downloader):
    def __init__(self, parent, url):
        super(RedditDownloader, self).__init__(parent, "reddit", "Reddit", url)
        self.queue = []

    def convert_to_filename(self, url):
        return "reddit_" + super(RedditDownloader, self).convert_to_filename(url)

    @staticmethod
    def build_json_url(url):
        p = urlparse.urlparse(url)
        return p.scheme + '://' + p.netloc + p.path + '.json' + '?' + p.query + ('&' if p.query else '') + 'limit=100'

    @staticmethod
    def validate(url, parent=None):
        logger.info(lambda: "Validating Reddit url " + url)
        try:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "http://" + url

            if not '//reddit.com' in url and not '//www.reddit.com' in url:
                return False

            dl = RedditDownloader(parent, url)
            dl.fill_queue()
            return len(dl.queue) > 0
        except Exception:
            logger.exception(lambda: "Error while validating URL, probably no image posts for this URL")
            return False

    def download_one(self):
        logger.info(lambda: "Downloading an image from Reddit, " + self.location)
        logger.info(lambda: "Queue size: %d" % len(self.queue))

        if not self.queue:
            self.fill_queue()
        if not self.queue:
            logger.info(lambda: "Reddit queue empty after fill")
            return None

        origin_url, image_url, extra_metadata = self.queue.pop()
        return self.save_locally(origin_url, image_url, extra_metadata=extra_metadata)

    def fill_queue(self):
        logger.info(lambda: "Reddit URL: " + self.location)

        json_url = RedditDownloader.build_json_url(self.location)
        s = Util.fetch_json(json_url)
        for item in s['data']['children']:
            try:
                data = item['data']
                image_url = data['url']
                if re.match(r'^http(s)?://imgur\.com/\w+$', image_url):
                    image_url = image_url.replace('://', '://i.') + '.jpg'

                if image_url.lower().endswith(('.jpg', '.jpeg', '.png')):
                    src_url = 'http://www.reddit.com' + data['permalink']
                    extra_metadata = {'sourceType': 'reddit'}
                    if data['over_18']:
                        extra_metadata['sfwRating'] = 0
                        if self.parent and self.parent.options.safe_mode:
                            continue
                    self.queue.append((src_url, image_url, extra_metadata))
            except Exception:
                logger.exception(lambda: "Could not process an item in the Reddit json result")

        random.shuffle(self.queue)
        logger.info(lambda: "Reddit queue populated with %d URLs" % len(self.queue))