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

from variety.plugins.builtin.downloaders.ArtstationDownloader import (
    ArtstationDownloader,
)
from variety.plugins.downloaders.ConfigurableImageSource import (
    ConfigurableImageSource,
)
from variety.Util import _

random.seed()


logger = logging.getLogger("variety")


class ArtstationSource(ConfigurableImageSource):
    @classmethod
    def get_info(cls):
        return {
            "name": "ArtstationSource",
            "description": _(
                "Configurable source for fetching images from Art Station"
            ),
            "author": "Denis Gordeev",
            "version": "0.1",
        }

    def get_source_type(self):
        return "art_station"

    def get_source_name(self):
        return "Art Station"

    def get_ui_instruction(self):
        return _(
            "Enter the name of an artist or paste the full URL of their "
            "artstation page with .rss extenstion or without it. \n"
            "Example: You may specify simply 'kd428' or "
            "<a href='https://www.artstation.com/kd428'>https://www.artstation.com/kd428</a>\n"
            "Example: Or direct it to the RSS: "
            "<a href='https://www.artstation.com/kd428.rss'>https://www.artstation.com/kd428.rss</a>"
        )

    def get_ui_short_instruction(self):
        return _("URL or name of an artist: ")

    def get_ui_short_description(self):
        return _("Fetch images from a given artist")

    def validate(self, query):
        logger.info(lambda: "Validating ArtStation query " + query)
        if query.endswith("/"):
            query = query[:-1]
        if "artstation.com/artwork/" in query:
            logger.exception(lambda: "Error while validating URL, artwork url")
            return query, _("We cannot download individual artworks.")
        if "/" not in query:
            query = "https://www.artstation.com/%s" % query
        if not query.endswith(".rss"):
            query = query + ".rss"
        try:
            if not query.startswith("http://") and not query.startswith(
                "https://"
            ):
                query = "http://" + query

            if (
                not "//www.artstation.com" in query
                and not "//www.artstation.com" in query
            ):
                return False, _(
                    "This does not seem to be a valid ArtStation URL"
                )

            dl = ArtstationDownloader(self, query)
            queue = dl.fill_queue()
            return (
                query,
                None
                if len(queue) > 0
                else _("We could not find any image submissions there."),
            )
        except Exception:
            logger.exception(
                lambda: "Error while validating URL, probably no image posts for this URL"
            )
            return query, _("We could not find any image submissions there.")

    def create_downloader(self, config):
        return ArtstationDownloader(self, config)
