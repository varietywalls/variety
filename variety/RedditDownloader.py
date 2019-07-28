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

from variety.plugins.downloaders.DefaultDownloader import DefaultDownloader
from variety.plugins.downloaders.ImageSource import ImageSource
from variety.Util import Util, _

logger = logging.getLogger("variety")

random.seed()


class RedditDownloader(ImageSource, DefaultDownloader):
    def __init__(self, parent, url):
        ImageSource.__init__(self)
        DefaultDownloader.__init__(self, source=self, config=url)
        self.set_variety(parent)

    @classmethod
    def get_info(cls):
        raise Exception("Not yet implemented as a plugin")

    def get_source_type(self):
        return "reddit"

    def get_description(self):
        return _("Images from subreddits at Reddit")

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

    @staticmethod
    def validate(url, parent=None):
        logger.info(lambda: "Validating Reddit url " + url)
        try:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "http://" + url

            if not "//reddit.com" in url and not "//www.reddit.com" in url:
                return False

            dl = RedditDownloader(parent, url)
            queue = dl.fill_queue()
            return len(queue) > 0
        except Exception:
            logger.exception(
                lambda: "Error while validating URL, probably no image posts for this URL"
            )
            return False

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
