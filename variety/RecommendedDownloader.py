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
from variety.Downloader import Downloader
from variety.Util import Util
from variety.Smart import Smart
from variety.AttrDict import AttrDict

logger = logging.getLogger('variety')

random.seed()


class RecommendedDownloader(Downloader):
    def __init__(self, parent):
        super(RecommendedDownloader, self).__init__(parent, "Recommended by Variety", "Recommended")
        self.queue = []

    def download_one(self):
        logger.info("Downloading a Recommended by Variety image")
        logger.info("Queue size: %d" % len(self.queue))

        if not self.queue:
            self.fill_queue()
        if not self.queue:
            logger.info("Recommended queue still empty after fill request")
            return None

        url, image_url, source_name, source_location = self.queue.pop()
        logger.info("Recommended URL: " + url)
        return self.save_locally(url, image_url, source_name, source_location)

    def fill_queue(self):
        logger.info("Filling Recommended queue")
        self.parent.smart.load_user()
        recommended_url = Smart.API_URL + '/user/' + self.parent.smart.user["id"] + '/recommended/json'
        recommended = map(AttrDict, Util.fetch_json(recommended_url))
        for image in recommended:
            if not image.image_url or not image.sources:
                continue
            if image.width and image.height and not self.parent.size_ok(image.width, image.height):
                continue
            self.queue.append((image.origin_url, image.image_url, image.sources[0][0], image.sources[0][1]))

        logger.info("Recommended queue populated with %d URLs" % len(self.queue))
