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

from requests import HTTPError

from variety.plugins.builtin.downloaders.EuropeanaDownloader import EuropeanaDownloader
from variety.plugins.downloaders.ConfigurableImageSource import ConfigurableImageSource
from variety.plugins.downloaders.DefaultDownloader import DefaultDownloader
from variety.plugins.downloaders.ImageSource import Throttling
from variety.Util import Util, _

logger = logging.getLogger("variety")

random.seed()


class UnsupportedConfig(Exception):
    pass


class EuropeanaConfigurableSource(ConfigurableImageSource):
    class EuropeanaConfigurableDownloader(EuropeanaDownloader):
        def __init__(self, source, config):
            DefaultDownloader.__init__(self, source, config)
            self.set_variety(source.get_variety())

        def get_source_type(self):
            return self.source.get_source_type()

        def get_description(self):
            return self.config

        def get_folder_name(self):
            return super(DefaultDownloader, self).get_folder_name()

        def get_europeana_api_url(self):
            return super().get_europeana_api_url()

    @classmethod
    def get_info(cls):
        return {
            "name": "EuropeanaConfigurableSource",
            "description": _("Configurable source for fetching photos from Europeana.com"),
            "author": "Andrea Pasquali",
            "version": "0.1",
        }

    def get_source_type(self):
        return "europeana-search"

    def validate(self, config):
        try:
            url = self.EuropeanaConfigurableDownloader(self, config).get_europeana_api_url()
            data = Util.fetch_json(url)
            valid = data.get("success") == True
            return config, None if valid else _("No images found")
        except UnsupportedConfig:
            return config, _("Something's wrong with your search parameter")
        except Exception as e:
            if isinstance(e, HTTPError) and e.response.status_code == 404:
                return config, _("No images found")
            else:
                return config, _("Oops, this didn't work. Is the remote service up?")

    def create_downloader(self, config):
        return self.EuropeanaConfigurableDownloader(self, config)

    def get_ui_instruction(self):
        return _(
            "We use the <a href='https://europeana.eu'>Europeana</a> APIs to fetch artwork images.\n"
            "\n"
            "You can request your own API key for free at <a href='https://www.europeana.eu/account/api-keys'>Europeana API</a>.\n"
        )

    def get_ui_short_instruction(self):
        return _("API key: ")

    def get_ui_short_description(self):
        return _("Fetch artwork images from Europeana.eu")

    def get_source_name(self):
        return "Europeana"

    def get_default_throttling(self):
        return Throttling(max_downloads_per_hour=120, max_queue_fills_per_hour=20)

    def on_image_set_as_wallpaper(self, img, meta):
        return EuropeanaDownloader().on_image_set_as_wallpaper(img, meta)
