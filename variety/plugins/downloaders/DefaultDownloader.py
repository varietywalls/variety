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
import logging
import os

from variety.plugins.downloaders.Downloader import Downloader
from variety.Util import Util

logger = logging.getLogger("variety")

QueueItem = collections.namedtuple("QueueItem", ["origin_url", "image_url", "extra_metadata"])


SAFE_MODE_BLACKLIST = {
    # Sample of Wallhaven and Flickr tags that cover most not-fully-safe images
    "woman",
    "women",
    "model",
    "models",
    "boob",
    "boobs",
    "tit",
    "tits",
    "lingerie",
    "bikini",
    "bikini model",
    "sexy",
    "bra",
    "bras",
    "panties",
    "face",
    "faces",
    "legs",
    "feet",
    "pussy",
    "ass",
    "asses",
    "topless",
    "long hair",
    "lesbians",
    "cleavage",
    "brunette",
    "brunettes",
    "redhead",
    "redheads",
    "blonde",
    "blondes",
    "high heels",
    "miniskirt",
    "stockings",
    "anime girls",
    "in bed",
    "kneeling",
    "girl",
    "girls",
    "nude",
    "naked",
    "people",
    "fuck",
    "sex",
}


class DefaultDownloader(Downloader, metaclass=abc.ABCMeta):
    def __init__(self, source, config=None):
        super().__init__(source, config)
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

    def download_queue_item(self, queue_item):
        """
        Unpacks the queue item (as populated by fill_queue) into arguments to pass to save_locally,
        and calls it. By default this assumes QueueItems are returned, but subclasses may choose a
        different represetnation for the queue items, and may also want to perform additional actions
        before calling save_locally (e.g. additional data fetching and parsing).
        Override if some work needs to be done on every queue item before it can be downloaded.
        :param queue_item: the queue item, as populated into the queue by fill_queue
        :return whatever the call to save_locally returns i.e. either the local file path in case
        of success, or None otherwise
        """
        origin_url, image_url, extra_metadata = queue_item
        return self.save_locally(origin_url, image_url, extra_metadata=extra_metadata)

    def download_one(self):
        """
        Provides a default implementation which relies on fill_queue, and takes the image source
        throttling into account.
        :return: path to the newly downloaded file, or None if the download attempt ws unsuccessful
        """
        if self.target_folder is None:
            raise Exception("update_download_folder was not called before downloading")

        name = self.get_source_name()
        max_downloads_per_hour, max_queue_fills_per_hour = self.source.get_throttling()

        if not self.source.is_download_allowed():
            logger.info(
                lambda: "%s: max_downloads_per_hour of %d reached, skip this attempt"
                % (name, max_downloads_per_hour)
            )
            return None

        logger.info(lambda: "%s: Downloading an image, config: %s" % (name, self.config))
        logger.info(lambda: "%s: Queue size: %d" % (name, len(self.queue)))

        if not self.queue:
            if not self.source.is_fill_queue_allowed():
                logger.info(
                    lambda: "%s: Queue empty, but max_queue_fills_per_hour of %d reached, "
                    "will try again later" % (name, max_queue_fills_per_hour)
                )
                return None

            self.source.register_fill_queue()
            logger.info(lambda: "%s: Filling queue" % name)
            items = self.fill_queue()
            for item in items:
                self.queue.append(item)

        if not self.queue:
            logger.info(lambda: "%s: Queue still empty after fill request" % name)
            return None
        else:
            logger.info(lambda: "%s: Queue populated with %d URLs" % (name, len(self.queue)))

        self.source.register_download()
        queue_item = self.queue.pop()
        return self.download_queue_item(queue_item)

    def is_in_downloaded(self, image_url):
        return os.path.exists(self._local_filepath(url=image_url))

    def is_in_banned(self, origin_url):
        return self.get_variety() and origin_url in self.get_variety().banned

    def is_safe_mode_enabled(self):
        return self.get_variety() and self.get_variety().options.safe_mode

    def is_unsafe(self, extra_metadata):
        if self.is_safe_mode_enabled() and "keywords" in extra_metadata:
            blacklisted = set(k.lower() for k in extra_metadata["keywords"]) & SAFE_MODE_BLACKLIST
            return (True, blacklisted) if len(blacklisted) > 0 else (False, [])
        return False, []

    def is_size_inadequate(self, width, height):
        return self.get_variety() and not self.get_variety().size_ok(width, height)

    def is_in_favorites(self, url):
        return self.get_variety() and os.path.exists(
            os.path.join(self.get_variety().options.favorites_folder, Util.get_local_name(url))
        )

    def save_locally(
        self,
        origin_url,
        image_url,
        source_type=None,
        source_location=None,
        source_name=None,
        force_download=False,
        extra_metadata=None,
        local_filename=None,
        request_headers=None,
        request_kwargs=None,
        check_image=False,
    ):
        source_type = source_type or self.get_source_type()
        source_name = source_name or self.get_source_name()
        source_location = source_location or self.get_source_location() or self.get_description()

        if not force_download and self.is_in_banned(origin_url):
            logger.info(lambda: "URL " + origin_url + " is banned, skip downloading")
            return None

        try:
            os.makedirs(self.target_folder)
        except Exception:
            pass

        if origin_url.startswith("//"):
            origin_url = "https:" + origin_url

        if image_url.startswith("//"):
            image_url = origin_url.split("//")[0] + image_url

        # we will download the contents to a ".partial" file, then rename it to the proper name
        if not local_filename:
            local_filename = self.get_local_filename(url=image_url)
        local_filepath = self._local_filepath(local_filename=local_filename)
        local_filepath_partial = local_filepath + ".partial"
        logger.info(lambda: "Origin URL: " + origin_url)
        logger.info(lambda: "Image URL: " + image_url)
        logger.info(lambda: "Local path: " + local_filepath)

        if not force_download and os.path.exists(local_filepath):
            logger.info(lambda: "File already exists, skip downloading")
            return None

        is_unsafe, blacklisted = self.is_unsafe(extra_metadata or {})
        if is_unsafe:
            logger.info(
                lambda: "Skipping non-safe download %s due to blacklisted keywords (%s). "
                "Is the source %s:%s suitable for Safe mode?"
                % (origin_url, str(blacklisted), source_type, source_location)
            )
            return None

        try:
            r = Util.request(
                image_url, stream=True, headers=request_headers, **(request_kwargs or {})
            )
            with open(local_filepath_partial, "wb") as f:
                Util.request_write_to(r, f)
        except Exception as e:
            logger.info(
                lambda: "Download failed from image URL: %s (source location: %s) "
                % (image_url, source_location)
            )
            Util.safe_unlink(local_filepath_partial)
            raise e

        if check_image and not Util.is_image(local_filepath_partial, check_contents=True):
            logger.info(lambda: "Downloaded data was not an image, image URL might be outdated")
            Util.safe_unlink(local_filepath_partial)
            return None

        metadata = {
            "sourceType": source_type,
            "sourceName": source_name,
            "sourceLocation": source_location,
            "sourceURL": origin_url,
            "imageURL": image_url,
        }
        metadata.update(extra_metadata or {})
        Util.write_metadata(local_filepath_partial, metadata)

        # file rename is an atomic operation, so we should never end up with partial downloads
        os.rename(local_filepath_partial, local_filepath)
        logger.info(lambda: "Download complete")
        return local_filepath
