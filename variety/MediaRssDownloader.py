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
import xml.etree.ElementTree as ET

import logging
from variety.Smart import Smart

from variety import Downloader
from variety.Util import Util

logger = logging.getLogger('variety')

random.seed()

MEDIA_NS = "{http://search.yahoo.com/mrss/}"
VARIETY_NS = "{http://vrty.org/}"

class MediaRssDownloader(Downloader.Downloader):
    def __init__(self, parent, url):
        super(MediaRssDownloader, self).__init__(parent, "mediarss", "Media RSS", url)
        self.queue = []

    def convert_to_filename(self, url):
        return "mediarss_" + super(MediaRssDownloader, self).convert_to_filename(url)

    @staticmethod
    def fetch(url):
        content = Util.fetch_bytes(url)
        return ET.fromstring(content)

    @staticmethod
    def is_valid_content(x):
        return x is not None and "url" in x.attrib and (
            Util.is_image(x.attrib["url"]) or
            ("medium" in x.attrib and x.attrib["medium"].lower() == "image") or
            ("type" in x.attrib and x.attrib["type"].lower().startswith("image/"))
        )

    @staticmethod
    def validate(url):
        logger.info(lambda: "Validating MediaRSS url " + url)
        try:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url

            s = MediaRssDownloader.fetch(url)
            walls = [x.attrib["url"] for x in s.findall(".//{0}content".format(MEDIA_NS))
                     if MediaRssDownloader.is_valid_content(x)]
            return len(walls) > 0
        except Exception:
            logger.exception(lambda: "Error while validating URL, probably not a MediaRSS feed")
            return False

    def download_one(self):
        logger.info(lambda: "Downloading an image from MediaRSS, " + self.location)
        logger.info(lambda: "Queue size: %d" % len(self.queue))

        if not self.queue:
            self.fill_queue()
        if not self.queue:
            logger.info(lambda: "MediaRSS queue empty after fill")
            return None

        origin_url, image_url, source_type, source_location, source_name, extra_metadata = self.queue.pop()
        parse = urlparse.urlparse(origin_url)
        host = parse.netloc if hasattr(parse, "netloc") else "origin"
        return self.save_locally(origin_url, image_url, source_type or 'mediarss',
                                 source_location, source_name or host, extra_metadata=extra_metadata)

    @staticmethod
    def picasa_hack(feed_url):
        """ Picasa hack - by default Picasa's RSS feeds link to low-resolution images.
        Add special parameter to request the full-resolution instead:"""
        if feed_url.find("://picasaweb.") > 0:
            logger.info(lambda: "Picasa hack to get full resolution images: add imgmax=d to the feed URL")
            feed_url = feed_url.replace("&imgmax=", "&imgmax_disabled=")
            feed_url += "&imgmax=d"
            logger.info(lambda: "Final Picasa feed URL: " + feed_url)

        return feed_url

    def fill_queue(self):
        logger.info(lambda: "MediaRSS URL: " + self.location)
        feed_url = self.location
        feed_url = MediaRssDownloader.picasa_hack(feed_url)

        s = self.fetch(feed_url)

#        try:
#            self.channel_title = s.find("channel/title").text
#        except Exception:
#            self.channel_title = "origin"
#
        for item in s.findall(".//item"):
            try:
                origin_url = item.find("link").text
                group = item.find("{0}group".format(MEDIA_NS))
                content = None
                width = -1
                if group is not None:
                    # find the largest image in the group
                    for c in group.findall("{0}content".format(MEDIA_NS)):
                        try:
                            if MediaRssDownloader.is_valid_content(c):
                                if content is None:
                                    content = c # use the first one, in case we don't find any width info
                                if "width" in c.attrib and int(c.attrib["width"]) > width:
                                    content = c
                                    width = int(c.attrib["width"])
                        except Exception:
                            pass
                else:
                    content = item.find("{0}content".format(MEDIA_NS))

                if not MediaRssDownloader.is_valid_content(content):
                    continue

                source_name = None
                source_location = None
                source_type = None
                variety_source = item.find("{0}source".format(VARIETY_NS))
                if variety_source is not None:
                    source_name = variety_source.attrib.get('name', None)
                    source_location = variety_source.attrib.get('location', None)
                    source_type = variety_source.attrib.get('type', None)

                extra_metadata = {}

                try:
                    extra_metadata['headline'] = item.find("{0}title".format(MEDIA_NS)).text
                except:
                    try:
                        extra_metadata['headline'] = item.find("title").text
                    except:
                        pass

                try:
                    extra_metadata['description'] = item.find("{0}description".format(MEDIA_NS)).text
                except:
                    pass

                try:
                    author = item.find("{0}author".format(VARIETY_NS))
                    if author is not None:
                        extra_metadata['author'] = author.attrib.get('name', None)
                        extra_metadata['authorURL'] = author.attrib.get('url', None)
                    else:
                        extra_metadata['author'] = item.find("{0}credit".format(MEDIA_NS)).text
                except:
                    pass

                try:
                    sfw = item.find("{0}sfw_info".format(VARIETY_NS))
                    if sfw is not None:
                        rating = int(sfw.attrib.get('rating', None))
                        extra_metadata['sfwRating'] = rating

                        if self.parent and self.parent.options.safe_mode and rating < 100:
                            logger.info(lambda: "Skipping non-safe download from VRTY MediaRss feed. "
                                                "Is the source %s suitable for Safe mode?" % self.location)
                            continue
                except:
                    pass

                try:
                    extra_metadata['keywords'] = map(lambda k: k.strip(), item.find("{0}keywords".format(MEDIA_NS)).text.split(','))
                except:
                    pass

                self.process_content(origin_url, content, source_type, source_location, source_name, extra_metadata)
            except Exception:
                logger.exception(lambda: "Could not process an item in the Media RSS feed")

        random.shuffle(self.queue)
        logger.info(lambda: "MediaRSS queue populated with %d URLs" % len(self.queue))

    def process_content(self, origin_url, content, source_type=None, source_location=None, source_name=None, extra_metadata={}):
        try:
            logger.debug(lambda: "Checking origin_url " + origin_url)

            if self.parent and origin_url in self.parent.banned:
                logger.debug(lambda: "In banned, skipping")
                return

            image_file_url = content.attrib["url"]

            if self.is_in_downloaded(image_file_url):
                logger.debug(lambda: "Already in downloaded")
                return

            if self.is_in_favorites(image_file_url):
                logger.debug(lambda: "Already in favorites")
                return

            width = None
            height = None
            try:
                width = int(content.attrib["width"])
                height = int(content.attrib["height"])
            except Exception:
                pass

            if self.parent and width and height and not self.parent.size_ok(width, height):
                logger.debug(lambda: "Small or non-landscape size/resolution")
                return

            logger.debug(lambda: "Appending to queue %s, %s, %s, %s, %s" %
                         (origin_url, image_file_url, source_type, source_location, source_name))
            self.queue.append((origin_url, image_file_url, source_type, source_location, source_name, extra_metadata))
        except Exception:
            logger.exception(lambda: "Error parsing single MediaRSS image info:")
