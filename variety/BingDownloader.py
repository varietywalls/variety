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
import logging
from datetime import datetime
from variety import Downloader
from variety.Util import Util

logger = logging.getLogger('variety')

random.seed()


class BingDownloader(Downloader.Downloader):
    BING_JSON_URL = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=100&mkt=en-US"  # n=100, but max 8 images are actually returned... Pity.

    def __init__(self, parent):
        super(BingDownloader, self).__init__(parent, "bing", "Bing", "https://www.bing.com/gallery/")
        self.queue = []

    def convert_to_filename(self, url):
        return "Bing"

    def download_one(self):
        logger.info(lambda: "Downloading an image from Bing")
        logger.info(lambda: "Queue size: %d" % len(self.queue))

        if not self.queue:
            self.fill_queue()
        if not self.queue:
            logger.info(lambda: "Bing queue empty after fill")
            return None

        origin_url, image_url, extra_metadata = self.queue.pop()
        return self.save_locally(origin_url, image_url, extra_metadata=extra_metadata)

    def fill_queue(self):
        logger.info(lambda: "Filling Bing queue from " + self.location)

        s = Util.fetch_json(BingDownloader.BING_JSON_URL)
        for item in s['images']:
            try:
                image_url = 'https://www.bing.com' + item['url']
                filename = item['url'].split('/')[-1]
                name = filename[0:filename.find('_EN')]
                src_url = 'https://www.bing.com/gallery/#images/%s' % name
                try:
                    date = datetime.strptime(item['startdate'], '%Y%m%d').strftime('%Y-%m-%d')
                except:
                    date = item['startdate']
                extra_metadata = {
                    'sourceType': 'bing',
                    'sfwRating': 100,
                    'headline': 'Bing Photo of the Day, %s' % date,
                    'description': item['copyright'],
                }
                self.queue.append((src_url, image_url, extra_metadata))
            except:
                logger.exception(lambda: "Could not process an item in the Bing json result")

        random.shuffle(self.queue)
        logger.info(lambda: "Bing queue populated with %d URLs" % len(self.queue))