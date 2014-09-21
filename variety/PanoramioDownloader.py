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
import os
import urllib
import json
import random

import logging
import time
from variety import Downloader
from variety.Util import Util
from variety_lib import varietyconfig

logger = logging.getLogger('variety')

random.seed()

class PanoramioDownloader(Downloader.Downloader):
    API_URL = "http://www.panoramio.com/map/get_panoramas.php?set=public&from=%d&to=%d&minx=%s&miny=%s&maxx=%s&maxy=%s&size=original"

    last_download_time = 0

    def __init__(self, parent, location):
        super(PanoramioDownloader, self).__init__(parent, "panoramio", "Panoramio", location)
        self.parse_location()
        self.last_fill_time = 0
        self.queue = []

    def convert_to_filename(self, url):
        return "panoramio_" + super(PanoramioDownloader, self).convert_to_filename(url)

    def parse_location(self):
        data = json.loads(self.location)
        self.minx = data['minx']
        self.miny = data['miny']
        self.maxx = data['maxx']
        self.maxy = data['maxy']

    def search(self, _from, _to):
        url = PanoramioDownloader.API_URL % (_from, _to, self.minx, self.miny, self.maxx, self.maxy)
        logger.info("Performing Panoramio API call: url=%s" % url)
        return Util.fetch_json(url)

    def download_one(self):
        min_download_interval, min_fill_queue_interval = self.parse_server_options("panoramio", 0, 0)

        if time.time() - PanoramioDownloader.last_download_time < min_download_interval:
            logger.info("Minimal interval between Panoramio downloads is %d, skip this attempt" % min_download_interval)
            return None

        logger.info("Downloading an image from Panoramio, " + self.location)
        logger.info("Queue size: %d" % len(self.queue))

        if not self.queue:
            if time.time() - self.last_fill_time < min_fill_queue_interval:
                logger.info("Panoramio queue empty, but minimal interval between fill attempts is %d, "
                            "will try again later" % min_fill_queue_interval)
                return None

            self.fill_queue()

        if not self.queue:
            logger.info("Panoramio queue still empty after fill request")
            return None

        PanoramioDownloader.last_download_time = time.time()

        photo = self.queue.pop()
        image = self.save_locally(photo["photo_url"],
                                 photo["photo_file_url"],
                                 extra_metadata={"author": photo["owner_name"],
                                                 "authorURL": photo["owner_url"]})

        # Uncomment to overlay Panoramio logo:
        # logo = os.path.join(varietyconfig.get_data_path(), 'panoramio/logo.png')
        # logo_command = u"mogrify -gravity SouthEast -draw 'image Over 70,70 0,0 \"%s\"' \"%s\"" % (logo, image)
        # os.system(logo_command.encode('utf8'))

        return image

    def fill_queue(self):
        self.last_fill_time = time.time()

        logger.info("Filling Panoramio queue: " + self.location)

        total_count = int(self.search(0, 0)["count"])
        _from = random.randint(0, max(0, total_count - 100))
        _to = min(_from + 100, total_count)

        data = self.search(_from, _to)

        for photo in data["photos"]:
            try:
                width = int(photo["width"])
                height = int(photo["height"])
                if self.parent and not self.parent.size_ok(width, height):
                    continue
                if self.parent and photo["photo_url"] in self.parent.banned:
                    continue
            except Exception:
                # consider ok
                pass

            self.queue.append(photo)

        random.shuffle(self.queue)

        if len(self.queue) >= 20:
            self.queue = self.queue[:len(self.queue)//2]
            # only use randomly half the images - if we ever hit the same page again, we'll still have what to download

        logger.info("Panoramio queue populated with %d URLs" % len(self.queue))
