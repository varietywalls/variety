# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (c) 2026, Andrea Pasquali <andreapasquali97@gmail.com>
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
import logging, random
from urllib.parse import urlencode

from variety.plugins.downloaders.ImageSource import Throttling
from variety.plugins.downloaders.SimpleDownloader import SimpleDownloader
from variety.Util import Util, _

logger = logging.getLogger("variety")

random.seed()


class EuropeanaDownloader(SimpleDownloader):

    DESCRIPTION = _("Europe's digital cultural heritage from Europeana.eu")

    # This API key has been requested from Andrea Pasquali to Europeana.ue in order to use it for Variety project
    API_KEY = "damolystist"

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
        return Throttling(max_downloads_per_hour=120, max_queue_fills_per_hour=4)

    def get_europeana_api_url(self):
        base_url = "https://api.europeana.eu/record/v2/search.json"
        query_params = urlencode({
            "wskey": EuropeanaDownloader.API_KEY,
            "query": f"{self.config if self.config else ''}(painting OR watercolor OR canvas OR artwork) NOT photograph NOT manuscript NOT print NOT book",
            "sort": "random",
            "rows": 30,
            "profile": "minimal",
            "reusability": "open",
            "media": "true",
            "completeness": "[1 TO 10]",
            "collection": "art",
            "type": "IMAGE",
            "img_color": "true",
            "img_size": "extra_large",
            "img_ratio": "landscape"
        })
        return f"{base_url}?{query_params}"

    def fill_queue(self):

        url = self.get_europeana_api_url()
        logger.info(lambda: "Filling Europeana queue from " + url)

        r = Util.request(url)
        queue = []
        for item in r.json()["items"]:
            try:

                image_url = item["edmIsShownBy"][0]
                origin_url = item["guid"]

                author = [
                    creator
                    for creator in (
                        item["dcCreator"] if item.get("dcCreator", None) else []
                    )
                    if "http" not in creator
                ]
                author = author[0] if len(author) > 0 else item["dataProvider"][0]
                author_url = [
                    creator
                    for creator in (item["dcCreator"] if item.get("dcCreator", None) else [])
                    if "http" in creator
                ]
                artwork_url = item['edmIsShownAt'][0] if item.get('edmIsShownAt') else origin_url
                extra_metadata = {
                    "sourceType": "europeana",
                    "headline": item["title"][-1],
                    "author": author,
                    "authorURL": author_url[0] if len(author_url) > 0 else artwork_url,
                    "description": item["dcDescription"][0][:10000] if item.get("dcDescription") else None,
                    "keywords": [],
                    "extraData": {
                        "provider": item["dataProvider"][0],
                    },
                }

                queue.append((origin_url, image_url, extra_metadata))
            except:
                logger.exception(lambda: "Could not process an item from Europeana")
                raise

        return queue