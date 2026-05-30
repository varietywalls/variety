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
import urllib.parse

from variety.plugins.downloaders.DefaultDownloader import DefaultDownloader
from variety.Util import Util, _

logger = logging.getLogger("variety")

random.seed()

FLICKR_API_URL = "https://www.flickr.com/services/rest/"


class FlickrDownloader(DefaultDownloader):
    def __init__(self, source, config, api_key):
        DefaultDownloader.__init__(self, source=source, config=config)
        self.api_key = api_key

    def get_source_type(self):
        return "flickr"

    def get_description(self):
        return "Flickr"

    def fill_queue(self):
        queue = []
        logger.info(lambda: "Flickr search: " + self.config)

        params = {"method": "flickr.photos.search", "format": "json", "nojsoncallback": "1"}

        if self.api_key:
            params["api_key"] = self.api_key
        else:
            logger.warning("No Flickr API key provided, using public access (very limited)")
            params["api_key"] = "1250c59d781d5d2e07ab1e73b6a47d05"

        # Parse config which can be: user_id, group_id, tags, text, etc.
        for item in self.config.split(";"):
            if not item:
                continue
            if ":" in item:
                key, value = item.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key == "user_id":
                    params["user_id"] = value
                elif key == "group_id":
                    params["group_id"] = value
                elif key == "tags":
                    params["tags"] = value
                elif key == "text":
                    params["text"] = value

        params["per_page"] = "100"
        params["extras"] = "url_l,url_o,owner_name,date_taken"

        url = FLICKR_API_URL + "?" + urllib.parse.urlencode(params)
        logger.info(lambda: "Flickr API URL: " + url)

        try:
            data = Util.fetch_json(url)
            if data.get("stat") == "fail":
                logger.warning("Flickr API error: " + str(data.get("message", "")))
                return []

            photos = data.get("photos", {}).get("photo", [])
            for photo in photos:
                try:
                    # Prefer url_l (large) or url_o (original)
                    image_url = photo.get("url_l") or photo.get("url_o")
                    if not image_url:
                        continue

                    origin_url = photo.get("id", "")
                    if origin_url:
                        origin_url = "https://www.flickr.com/photos/{}/{}".format(
                            photo.get("owner", ""), origin_url
                        )

                    extra_metadata = {
                        "author": photo.get("ownername", ""),
                        "description": photo.get("title", ""),
                    }

                    queue.append((origin_url, image_url, "flickr", "https://www.flickr.com", "Flickr", extra_metadata))
                except Exception:
                    logger.exception("Error processing Flickr photo")

        except Exception:
            logger.exception("Error fetching Flickr photos")

        random.shuffle(queue)
        return queue

    def download_queue_item(self, queue_item):
        origin_url, image_url, source_type, source_location, source_name, extra_metadata = queue_item
        return self.save_locally(origin_url, image_url, source_type, source_location, source_name, extra_metadata=extra_metadata)