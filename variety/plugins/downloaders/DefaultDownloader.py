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
import abc
import collections
import os
import time
import logging

from variety.plugins.downloaders.Downloader import Downloader
from variety.Util import Util

logger = logging.getLogger('variety')

QueueItem = collections.namedtuple('QueueItem', ['origin_url', 'image_url', 'extra_metadata'])


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


class DefaultDownloader(Downloader, metaclass=abc.ABCMeta):
    def __init__(self, source, description, folder_name, config=None, full_descriptor=None):
        super().__init__(source, description, folder_name, config, full_descriptor)
        self.queue = []

    @abc.abstractmethod
    def fill_queue(self):
        """
        Subclasses should implement this method. It should return one or more QueueItems.
        This serves as a cache so that downloaders can prepare multiple items for downloading using
        fewer API/scrape calls. The size of the queue should be a compromise between making fewer API calls
        and keeping some variety in the consecutive downloads.
        :return: a list with one or more QueueItems
        """
        pass

    def download_one(self):
        name = self.get_source_name()
        min_download_interval, min_fill_queue_interval = self.source.get_throttling()

        if time.time() - self.source.last_download_time < min_download_interval:
            logger.info(lambda: "%s: Minimal interval between downloads is %d, skip this attempt" % (
                name, min_download_interval))
            return None

        logger.info(lambda: "%s: Downloading an image" % name)
        logger.info(lambda: "%s: Queue size: %d" % (name, len(self.queue)))

        if not self.queue:
            if time.time() - self.source.last_fill_time < min_fill_queue_interval:
                logger.info(lambda: "%s: Queue empty, but minimal interval between fill attempts is %d, "
                            "will try again later" % (name, min_fill_queue_interval))
                return None

            self.source.last_fill_time = time.time()
            logger.info(lambda: "%s: Filling queue" % name)
            items = self.fill_queue()
            for item in items:
                self.queue.append(item)

        if not self.queue:
            logger.info(lambda: "%s: Queue still empty after fill request" % name)
            return None

        self.source.last_download_time = time.time()

        origin_url, image_url, extra_metadata = self.queue.pop()
        return self.save_locally(
            self.target_folder, origin_url, image_url, extra_metadata=extra_metadata)

    def is_in_downloaded(self, url):
        return os.path.exists(self.get_local_filename(url))

    def is_in_favorites(self, url):
        return self.get_variety() and os.path.exists(
            os.path.join(self.get_variety().options.favorites_folder, Util.get_local_name(url)))

    def save_locally(self, origin_url, image_url,
                     source_type=None, source_location=None, source_name=None,
                     force_download=False, extra_metadata={}, local_filename=None):
        parent = self.get_variety()

        source_type = source_type or self.get_source_type()
        source_name = source_name or self.get_source_name()
        source_location = source_location or self.get_config() or self.get_description()

        if not force_download and parent and origin_url in parent.banned:
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

        if parent and parent.options.safe_mode and 'keywords' in extra_metadata:
            blacklisted = set(k.lower() for k in extra_metadata['keywords']) & SAFE_MODE_BLACKLIST
            if len(blacklisted) > 0:
                logger.info(lambda: "Skipping non-safe download %s due to blacklisted keywords (%s). "
                                    "Is the source %s:%s suitable for Safe mode?" %
                                    (origin_url, str(blacklisted), source_type, source_location))
                return None

        try:
            r = Util.request(image_url, stream=True)
            with open(local_filename, 'wb') as f:
                Util.request_write_to(r, f)
        except Exception as e:
            logger.info(lambda: "Download failed from image URL: %s (source location: %s) " % (
                image_url, source_location))
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
