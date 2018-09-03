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

SAFE_MODE_BLACKLIST = {
    # Sample of Wallhaven and Flickr tags that cover most not-fully-safe images
    'woman', 'women', 'model', 'models', 'boob', 'boobs', 'tit', 'tits',
    'lingerie', 'bikini', 'bikini model', 'sexy', 'bra', 'bras', 'panties',
    'face', 'faces', 'legs', 'feet', 'pussy',
    'ass', 'asses', 'topless', 'long hair', 'lesbians', 'cleavage',
    'brunette', 'brunettes', 'redhead', 'redheads', 'blonde', 'blondes',
    'high heels', 'miniskirt', 'stockings', 'anime girls', 'in bed', 'kneeling',
    'girl', 'girls', 'nude', 'naked', 'people', 'fuck', 'sex'
}


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


def save_locally(downloader, origin_url, image_url,
                 source_type=None, source_location=None, source_name=None,
                 force_download=False, extra_metadata={}, local_filename=None):
    if not source_type:
        source_type = self.source_type
    if not source_name:
        source_name = self.name
    if not source_location:
        source_location = self.location

    if not force_download and self.parent and origin_url in self.parent.banned:
        logger.info(lambda: "URL " + origin_url + " is banned, skip downloading")
        return None

    try:
        os.makedirs(self.target_folder)
    except Exception:
        pass

    if origin_url.startswith('//'):
        origin_url = 'https:' + origin_url

    if image_url.startswith('//'):
        image_url = origin_url.split('//')[0] + image_url

    if not local_filename:
        local_filename = self.get_local_filename(image_url)
    logger.info(lambda: "Origin URL: " + origin_url)
    logger.info(lambda: "Image URL: " + image_url)
    logger.info(lambda: "Local name: " + local_filename)

    if not force_download and os.path.exists(local_filename):
        logger.info(lambda: "File already exists, skip downloading")
        return None

    if self.parent and self.parent.options.safe_mode and 'keywords' in extra_metadata:
        blacklisted = set(k.lower() for k in extra_metadata['keywords']) & SAFE_MODE_BLACKLIST
        if len(blacklisted) > 0:
            logger.info(lambda: "Skipping non-safe download %s due to blacklisted keywords (%s). "
                                "Is the source %s:%s suitable for Safe mode?" %
                                (origin_url, str(blacklisted), source_type, self.location))
            return None

    try:
        r = Util.request(image_url, stream=True)
        with open(local_filename, 'wb') as f:
            Util.request_write_to(r, f)
    except Exception as e:
        logger.info(lambda: "Download failed from image URL: %s (source location: %s) " % (image_url, self.location))
        raise e

    if not Util.is_image(local_filename, check_contents=True):
        logger.info(lambda: "Downloaded data was not an image, image URL might be outdated")
        os.unlink(local_filename)
        return None

    metadata = {
        "sourceType": source_type,
        "sourceName": source_name,
        "sourceLocation": source_location,
        "sourceURL": origin_url,
        "imageURL": image_url
    }
    metadata.update(extra_metadata)
    Util.write_metadata(local_filename, metadata)

    logger.info(lambda: "Download complete")
    return local_filename


def get_throttling_params(source, key):
    params = source.get_default_throttling()
    min_download_interval, min_fill_queue_interval = \
        params["min_download_interval"], params["min_fill_queue_interval"]
    name = source.get_source_name()

    try:
        logger.info(lambda: "%s: parsing serverside options" % name)
        options = source.jumble.parent.server_options[key]
        logger.info(lambda: "%s serverside options: %s" % (source.get_source_name(), str(options)))
    except Exception:
        logger.exception(lambda: "Could not parse %s serverside options, using defaults %d, %d" % (
            name, min_download_interval, min_fill_queue_interval))
        return min_download_interval, min_fill_queue_interval

    try:
        min_download_interval = int(options["min_download_interval"])
    except Exception:
        logger.exception(lambda: "Bad or missing min_download_interval")

    try:
        min_fill_queue_interval = int(options["min_fill_queue_interval"])
    except Exception:
        logger.exception(lambda: "Bad or missing min_fill_queue_interval")

    return min_download_interval, min_fill_queue_interval

