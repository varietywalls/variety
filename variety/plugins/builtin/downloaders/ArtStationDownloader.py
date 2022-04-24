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
import logging
import random

from variety.plugins.downloaders.DefaultDownloader import DefaultDownloader
from variety.Util import Util

logger = logging.getLogger("variety")


class ArtStationDownloader(DefaultDownloader):
    def __init__(self, source, url):
        DefaultDownloader.__init__(self, source=source, config=url)

    def fill_queue(self):
        logger.info(lambda: "ArtStation URL: " + self.config)

        queue = []
        # json_url = ArtStationDownloader.build_json_url(self.config)
        url = self.config
        s = Util.html_soup(url)
        author = s.find("channel").find("title").get_text().strip()
        author_url = s.find("channel").find("link").next.strip()
        items = s.findAll("item")
        for index, item in enumerate(items):
            try:
                extra_metadata = {
                    "headline": item.find("title").get_text().strip(),
                    "description": item.find("description").get_text().strip().replace("]]>", ""),
                    "author": author,
                    "authorURL": author_url,
                }
                src_url = item.find("guid").text + "#" + str(index)
                image_urls = [img["src"] for img in item.findAll("img")]
                for image_url in image_urls:
                    queue.append((src_url, image_url, extra_metadata))
            except Exception:
                logger.exception(lambda: "Could not process an item in the ArtStation rss result")

        random.shuffle(queue)
        return queue
