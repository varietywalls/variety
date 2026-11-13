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
import os
import random
import re
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from variety.plugins.downloaders.SimpleDownloader import SimpleDownloader
from variety.Util import Util, _

logger = logging.getLogger("variety")

random.seed()

# apod.nasa.gov now redirects to science.nasa.gov/apod, whose archive page is rendered with
# JavaScript, so the old archivepix.html scraping finds nothing. NASA exposes the same data via
# this WordPress REST endpoint (25 items per page max, newest first, ~1 page per 25 days).
API_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic"
PAGES_TO_SAMPLE_FROM = 29  # ~2 years of pictures


def _strip_html(html, prefix_re=None):
    text = BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)
    if prefix_re:
        text = re.sub(prefix_re, "", text).strip()
    return text or None


class APODDownloader(SimpleDownloader):
    DESCRIPTION = _("NASA Astro Pic of the Day")
    ROOT_URL = "https://science.nasa.gov/apod/"

    @classmethod
    def get_info(cls):
        return {
            "name": "APODDownloader",
            "description": APODDownloader.DESCRIPTION,
            "author": "Peter Levi",
            "version": "0.2",
        }

    def get_description(self):
        return APODDownloader.DESCRIPTION

    def get_source_type(self):
        return "apod"

    def get_source_name(self):
        return "NASA Astro Pic of the Day"

    def get_folder_name(self):
        return "nasa_apod"

    def get_source_location(self):
        return self.ROOT_URL

    def _fetch_page(self, page):
        items = Util.fetch_json("%s?page=%d&per_page=25" % (API_URL, page))
        if not isinstance(items, list):
            raise Exception("Unexpected APOD API response: %s" % str(items)[:200])
        return items

    def fill_queue(self):
        logger.info(lambda: "Filling APOD queue from %s" % API_URL)

        latest = self._fetch_page(1)
        try:
            older = self._fetch_page(random.randint(2, PAGES_TO_SAMPLE_FROM))
        except Exception:
            logger.exception(lambda: "Could not fetch older APOD page, using latest only")
            older = []

        def usable(item):
            return (
                item.get("media_type") == "image"
                and item.get("hdurl")
                and item.get("permalink")
                and not self.is_in_banned(item["permalink"])
            )

        latest = [x for x in latest if usable(x)]
        older = [x for x in older if usable(x)]

        queue = latest[:3]  # always put the latest 3 first
        rest = latest[3:] + older
        random.shuffle(rest)  # shuffle the rest
        queue.extend(rest)
        return queue

    def download_queue_item(self, item):
        origin_url = item["permalink"]
        image_url = item["hdurl"]
        logger.info(lambda: "APOD URL: %s, image URL: %s" % (origin_url, image_url))

        filename = os.path.basename(unquote(urlparse(image_url).path))
        if not filename:
            return None
        if item.get("date"):
            filename = "%s_%s" % (item["date"], filename)

        extra_metadata = {
            "headline": item.get("title"),
            "description": _strip_html(item.get("explanation"), r"^Explanation:\s*"),
            "author": _strip_html(
                item.get("credit") or item.get("copyright"), r"^(Image\s+)?Credit[^:]*:\s*"
            ),
        }
        extra_metadata = {k: v for k, v in extra_metadata.items() if v}

        return self.save_locally(
            origin_url,
            image_url,
            source_location=self.ROOT_URL,
            local_filename=filename,
            extra_metadata=extra_metadata,
        )
