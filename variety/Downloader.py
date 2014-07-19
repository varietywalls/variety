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
import string
import re
import logging
from variety.Util import Util

logger = logging.getLogger('variety')

class Downloader(object):
    def __init__(self, parent, name, location, is_refresher=False):
        self.parent = parent
        self.name = name
        self.location = location
        self.is_refresher = is_refresher

    def update_download_folder(self):
        filename = self.convert_to_filename(self.location)
        l = len(self.parent.real_download_folder)
        if len(filename) + l > 160:
            filename = filename[:(150 - l)] + Util.md5(filename)[:10]
        self.target_folder = os.path.join(self.parent.real_download_folder, filename)

    def convert_to_filename(self, url):
        url = re.sub(r"http://", "", url)
        url = re.sub(r"https://", "", url)
        valid_chars = "_%s%s" % (string.ascii_letters, string.digits)
        return ''.join(c if c in valid_chars else '_' for c in url)

    def get_local_filename(self, url):
        return os.path.join(self.target_folder, Util.get_local_name(url))

    def is_in_downloaded(self, url):
        return os.path.exists(self.get_local_filename(url))

    def is_in_favorites(self, url):
        return self.parent and os.path.exists(os.path.join(self.parent.options.favorites_folder, Util.get_local_name(url)))

    def save_locally(self, origin_url, image_url,
                     source_name=None, source_location=None, force_download=False, extra_metadata={}):
        if not source_name:
            source_name = self.name
        if not source_location:
            source_location = self.location

        if not force_download and origin_url in self.parent.banned:
            logger.info("URL " + origin_url + " is banned, skip downloading")
            return None

        try:
            os.makedirs(self.target_folder)
        except Exception:
            pass

        local_filename = self.get_local_filename(image_url)
        logger.info("Origin URL: " + origin_url)
        logger.info("Image URL: " + image_url)
        logger.info("Local name: " + local_filename)

        if not force_download and os.path.exists(local_filename):
            logger.info("File already exists, skip downloading")
            return None

        data = Util.fetch(image_url)
        with open(local_filename, 'wb') as f:
            f.write(data)

        if not Util.is_image(local_filename, check_contents=True):
            logger.info("Downloaded data was not an image, image URL might be outdated")
            os.unlink(local_filename)
            return None

        metadata = {
            "sourceName": source_name,
            "sourceLocation": source_location,
            "sourceURL": origin_url,
            "imageURL": image_url
        }
        metadata.update(extra_metadata)
        Util.write_metadata(local_filename, metadata)

        logger.info("Download complete")
        return local_filename

    def parse_server_options(self, key, default_min_download_interval, default_min_fill_queue_interval):
        min_download_interval = default_min_download_interval
        min_fill_queue_interval = default_min_fill_queue_interval

        try:
            logger.info("%s: parsing serverside options" % self.name)
            options = self.parent.server_options[key]
            logger.info("%s serverside options: %s" % (self.name, str(options)))
        except Exception:
            logger.exception("Could not parse %s serverside options, using defaults %d, %d" % (
                self.name, min_download_interval, min_fill_queue_interval))
            return min_download_interval, min_fill_queue_interval

        try:
            min_download_interval = int(options["min_download_interval"])
        except Exception:
            logger.exception("Bad or missing min_download_interval")

        try:
            min_fill_queue_interval = int(options["min_fill_queue_interval"])
        except Exception:
            logger.exception("Bad or missing min_fill_queue_interval")

        return min_download_interval, min_fill_queue_interval

