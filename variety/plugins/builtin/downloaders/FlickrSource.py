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

from variety.plugins.builtin.downloaders.FlickrDownloader import FlickrDownloader
from variety.plugins.downloaders.ConfigurableImageSource import ConfigurableImageSource
from variety.plugins.downloaders.ImageSource import Throttling
from variety.Util import _

logger = logging.getLogger("variety")

random.seed()


class FlickrSource(ConfigurableImageSource):
    @classmethod
    def get_info(cls):
        return {
            "name": "FlickrSource",
            "description": _("Configurable source for fetching images from Flickr"),
            "author": "Peter Levi",
            "version": "0.1",
        }

    def get_source_name(self):
        return "Flickr"

    def get_source_type(self):
        return "flickr"

    def get_default_throttling(self):
        return Throttling(max_downloads_per_hour=100, max_queue_fills_per_hour=10)

    def get_ui_instruction(self):
        return _(
            "<a href='https://www.flickr.com'>Flickr</a> is a popular image hosting service. "
            "You can provide a user URL, group URL, tags, or free-text search.\n"
            "\n"
            "Configuration format: user_id:...;group_id:...;tags:...;text:...\n"
            "Example (user): user_id:93647178@N00\n"
            "Example (tags): tags:landscape,nature\n"
            "Example (text): text:mountain sunset\n"
            "\n"
            "Get your own Flickr API key at: <a href='https://www.flickr.com/services/apps/create/'>https://www.flickr.com/services/apps/create/</a>\n"
            "Without an API key, access is very limited.\n"
            "\n"
            "Note: To use Flickr in Variety, you must set your API key in the Preferences dialog."
        )

    def get_ui_short_instruction(self):
        return _("Enter Flickr config (e.g. tags:landscape;user_id:...): ")

    def get_ui_short_description(self):
        return _("Fetch images from Flickr")

    def validate(self, config):
        try:
            api_key = self.variety.options.flickr_api_key if self.variety else ""
            downloader = FlickrDownloader(self, config, api_key)
            queue = downloader.fill_queue()
            return config, None if len(queue) > 0 else _("No images found")
        except Exception as e:
            logger.exception("Error validating Flickr source")
            return config, _("Error: {}").format(str(e))

    def create_downloader(self, config):
        api_key = self.variety.options.flickr_api_key if self.variety else ""
        return FlickrDownloader(self, config, api_key)