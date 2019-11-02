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

from downloaders.MediaRSSDownloader import MediaRSSDownloader
from variety.plugins.downloaders.ConfigurableImageSource import ConfigurableImageSource
from variety.Util import _

logger = logging.getLogger("variety")

random.seed()


class MediaRSSSource(ConfigurableImageSource):
    @classmethod
    def get_info(cls):
        return {
            "name": "MediaRSSSource",
            "description": _("Configurable source for fetching images from MediaRSS feeds"),
            "author": "Peter Levi",
            "version": "0.1",
        }

    def get_source_name(self):
        return "MediaRSS"

    def get_source_type(self):
        return "mediarss"

    def get_ui_instruction(self):
        return _(
            "Please paste the URL of the Media RSS feed below. Please note that only Media RSS "
            "feeds are supported, not arbitrary RSS feeds. Media RSS feeds contain media:content "
            "tags linking directly to the actual image content. "
            "Some examples of sites that provide Media RSS feeds are: "
            "<a href='https://picasaweb.google.com/'>Picasa</a>, "
            "<a href='http://www.deviantart.com'>deviantART</a>, "
            "<a href='http://www.smugmug.com/browse/'>SmugMug</a>, "
            "<a href='http://www.flickr.com'>Flickr</a>, "
            "<a href='http://interfacelift.com'>InterfaceLIFT</a>."
        )

    def get_ui_short_instruction(self):
        return _("Paste the URL of the Media RSS feed here: ")

    def get_ui_short_description(self):
        return _("Fetch images from a MediaRSS feed")

    def validate(self, url):
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        valid = MediaRSSDownloader.validate(url)
        error = _(
            "This does not seem to be a valid Media RSS feed URL or there is no content there."
        )
        return url, None if valid else error

    def create_downloader(self, config):
        return MediaRSSDownloader(self, config)
