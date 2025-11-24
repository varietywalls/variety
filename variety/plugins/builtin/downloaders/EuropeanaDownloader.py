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
import time

""" import requests
from PIL import Image
from io import BytesIO """

from variety.plugins.downloaders.ImageSource import Throttling
from variety.plugins.downloaders.SimpleDownloader import SimpleDownloader
from variety.Util import Util, _

logger = logging.getLogger("variety")

random.seed()


class EuropeanaDownloader(SimpleDownloader):
    DESCRIPTION = _("Europe's digital cultural heritage from Europeana.eu")

    API_KEY = ""
    rate_limiting_started_time = 0

    @classmethod
    def get_info(cls):
        return {
            "name": "EuropeanaDownloader",
            "description": EuropeanaDownloader.DESCRIPTION,
            "author": "Andrea Pasquali",
            "version": "0.1",
        }

    def get_source_type(self):
        return "Europeana"

    def get_description(self):
        return EuropeanaDownloader.DESCRIPTION

    def get_source_name(self):
        return "Europeana.eu"

    def get_source_location(self):
        return "https://www.europeana.eu"

    def get_folder_name(self):
        return "Europeana"

    def get_default_throttling(self):
        return Throttling(max_downloads_per_hour=10, max_queue_fills_per_hour=1)

    def get_europeana_api_url(self):
        url = "https://api.europeana.eu/record/v2/search.json?wskey={api_key}&query={query}&sort={sort}&rows={rows}&profile={profile}&reusability={reusability}&media={media}&qf=collection:{collection}&qf=TYPE:{type}&qf=IMAGE_COLOUR:{img_color}&qf=IMAGE_SIZE:{img_size}&qf=IMAGE_ASPECTRATIO:{img_ratio}&qf=MIME_TYPE:{mime}"
        return url.format(
            api_key = EuropeanaDownloader.API_KEY,
            query = "{keyword}(painting OR watercolor OR canvas OR artwork) NOT photograph NOT manuscript NOT print NOT book",
            sort = "random",
            rows = 30,
            profile = "minimal",
            reusability = "open",
            media = "true",
            collection = "art",
            type = "IMAGE",
            img_color = "true",
            img_size = "extra_large",
            img_ratio = "landscape",
            mime = "image/jpeg"
        )

    def fill_queue(self):
        if time.time() - EuropeanaDownloader.rate_limiting_started_time < 3600:
            logger.info(
                lambda: "Europeana queue empty, but rate limit reached, will try again later"
            )
            return []

        url = self.get_europeana_api_url()
        logger.info(lambda: "Filling Europeana queue from " + url)

        r = Util.request(url)
        queue = []
        for item in r.json()['items']:
            try:

                # Filter out the non landscape images
                """ image_headers_only = requests.get(url, stream=True, headers={'Range': 'bytes=0-24576'})
                img = Image.open(BytesIO(image_headers_only.content))
                width, height = img.size
                if self.is_size_inadequate(width, height):
                    continue """

                image_url = item["edmIsShownBy"][0]
                origin_url = item["edmIsShownAt"][0]

                author = [
                    creator for creator in
                    ( item["dcCreator"] if item.get("dcCreator", None) else ["Unknown"] )
                    if "http" not in creator
                ][0]
                author_url = [
                    creator for creator in
                    ( item["dcCreator"] if item.get("dcCreator", None) else [] )
                    if "http" in creator
                ]
                extra_metadata = {
                    "sourceType": "europeana",
                    "sfwRating": 100,
                    "author": author,
                    "authorURL": None if len(author_url) == 0 else author_url[0],
                    "description": item["title"][-1],
                    "keywords": [],
                    "extraData": {
                        "provider": item["dataProvider"],
                    },
                }

                queue.append((origin_url, image_url, extra_metadata))
            except:
                logger.exception(lambda: "Could not process an item from Europeana")
                raise

        random.shuffle(queue)
        return queue

    def on_image_set_as_wallpaper(self, img, meta):
        #extraData = meta.get("extraData", None)
        return