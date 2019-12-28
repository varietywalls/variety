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
import re
import urllib.parse

from plugins.downloaders.DefaultDownloader import DefaultDownloader
from variety import Util

logger = logging.getLogger("variety")


class RedditDownloader(DefaultDownloader):
    def __init__(self, source, url):
        DefaultDownloader.__init__(self, source=source, config=url)

    @staticmethod
    def build_json_url(url):
        p = urllib.parse.urlparse(url)
        return (
            p.scheme
            + "://"
            + p.netloc
            + p.path
            + ".json"
            + "?"
            + p.query
            + ("&" if p.query else "")
            + "limit=100"
        )

    def fill_queue(self):
        logger.info(lambda: "Reddit URL: " + self.config)

        queue = []
        json_url = RedditDownloader.build_json_url(self.config)
        s = Util.fetch_json(json_url)
        for item in s["data"]["children"]:
            try:
                data = item["data"]
                image_url = data["url"]
                if re.match(r"^http(s)?://imgur\.com/\w+$", image_url):
                    image_url = image_url.replace("://", "://i.") + ".jpg"

                if image_url.lower().endswith((".jpg", ".jpeg", ".png")):
                    src_url = "https://www.reddit.com" + data["permalink"]
                    extra_metadata = {"sourceType": "reddit"}
                    if data["over_18"]:
                        extra_metadata["sfwRating"] = 0
                        if self.is_safe_mode_enabled():
                            continue
                    queue.append((src_url, image_url, extra_metadata))
            except Exception:
                logger.exception(lambda: "Could not process an item in the Reddit json result")

        random.shuffle(queue)
        return queue
