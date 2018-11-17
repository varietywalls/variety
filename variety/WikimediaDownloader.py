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
from variety import Downloader
from variety.Util import Util

logger = logging.getLogger('variety')

WIKIMEDIA_ORIGIN_URL = "https://commons.wikimedia.org/w/api.php?action=featuredfeed&feed=potd&feedformat=rss"

class WikimediaDownloader(Downloader.Downloader):
    def __init__(self, parent):
        super(WikimediaDownloader, self).__init__(parent, "wikimedia", "Wikimedia Commons Picture of the Day", WIKIMEDIA_ORIGIN_URL)
        self.queue = []

    def convert_to_filename(self, url):
        return "Wikimedia"

    @staticmethod
    def fetch(url):
        return Util.xml_soup(url)

    def download_one(self):
        logger.info(lambda: "Downloading an image from Wikimedia Commons Picture of the Day, " + self.location)
        logger.info(lambda: "Queue size: %d" % len(self.queue))

        if not self.queue:
            self.fill_queue()
        if not self.queue:
            logger.info(lambda: "Wikimedia Commons queue still empty after fill request - probably nothing more to download")
            return None

        link, url = self.queue.pop()
        logger.info(lambda: "Wikimedia URL: " + url)
        return self.save_locally(link, url)

    def fill_queue(self):
        logger.info(lambda: "Filling Wikimedia queue from RSS")

        s = self.fetch(self.location)
        items = [x.find("description").contents[0] for x in s.findAll("item")]
        for item in s.findAll("item"):
            link = item.find("link").contents[0]
            description = item.find("description").contents[0]
            srcIndex = description.find("src=")
            urlIndex = description.find(".jpg", srcIndex)
            url = description[srcIndex+5:urlIndex+4].replace("/thumb", "")
            self.queue.append([link, url])

        logger.info(lambda: "Wikimedia queue populated with %d URLs" % len(self.queue))
