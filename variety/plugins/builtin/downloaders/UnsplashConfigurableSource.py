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

from variety.plugins.builtin.downloaders.UnsplashDownloader import UnsplashDownloader
from variety.plugins.downloaders.ConfigurableImageSource import ConfigurableImageSource
from variety.plugins.downloaders.DefaultDownloader import DefaultDownloader
from variety.plugins.downloaders.ImageSource import Throttling
from variety.Util import Util, _

logger = logging.getLogger("variety")

random.seed()


class UnsupportedConfig(Exception):
    pass


class UnsplashConfigurableSource(ConfigurableImageSource):
    class UnsplashConfigurableDownloader(UnsplashDownloader):
        def __init__(self, source, config):
            DefaultDownloader.__init__(self, source, config)
            self.set_variety(source.get_variety())

        def get_source_type(self):
            return self.source.get_source_type()

        def get_description(self):
            return self.config

        def get_folder_name(self):
            return super(DefaultDownloader, self).get_folder_name()

        def get_unsplash_api_url(self):
            self.config = self.config.replace("http://", "https://")
            params = {}
            if self.config.startswith("https://"):
                if self.config.startswith("https://unsplash.com/s/photos/"):
                    query = self.config.replace("https://unsplash.com/s/photos/", "").split("/")[0]
                    params["query"] = query
                elif self.config.startswith("https://unsplash.com/@"):
                    username = self.config.replace("https://unsplash.com/@", "").split("/")[0]
                    params["username"] = username
                elif self.config.startswith("https://unsplash.com/collections/"):
                    collections = self.config.replace(
                        "https://unsplash.com/collections/", ""
                    ).split("/")[0]
                    params["collections"] = collections
                else:
                    raise UnsupportedConfig()
            else:
                params["query"] = self.config

            return (
                super().get_unsplash_api_url()
                + "&"
                + "&".join("{}={}".format(key, value) for key, value in params.items())
            )

    @classmethod
    def get_info(cls):
        return {
            "name": "UnsplashConfigurableSource",
            "description": _("Configurable source for fetching photos from Unsplash.com"),
            "author": "Peter Levi",
            "version": "0.1",
        }

    def get_source_type(self):
        return "unsplash-search"

    def validate(self, config):
        try:
            url = self.UnsplashConfigurableDownloader(self, config).get_unsplash_api_url()
            data = Util.fetch_json(url)
            valid = "errors" not in data
            return config, None if valid else _("No images found")
        except UnsupportedConfig:
            return config, _("We do not support this type of URL")
        except Exception as e:
            if isinstance(e, HTTPError) and e.response.status_code == 404:
                return config, _("No images found")
            else:
                return config, _("Oops, this didn't work. Is the remote service up?")

    def create_downloader(self, config):
        return self.UnsplashConfigurableDownloader(self, config)

    def get_ui_instruction(self):
        return _(
            "We use the <a href='https://unsplash.com'>Unsplash</a> API to fetch random images "
            "that match the given search term or URL. The Unsplash API is rate-limited, so "
            "Variety fetches images from Unsplash sources as a reduced rate.\n"
            "\n"
            "Please specify either a search keyword, or the URL of a search result, user or "
            "collection.\n"
            "Example: <a href='https://unsplash.com/collections/3863203/desktop-wallpapers'>https://unsplash.com/collections/3863203/desktop-wallpapers</a>\n"
            "Example: <a href='https://unsplash.com/@pawel_czerwinski'>https://unsplash.com/@pawel_czerwinski</a>"
        )

    def get_ui_short_instruction(self):
        return _("Search keyword or URL: ")

    def get_ui_short_description(self):
        return _("Fetch images from Unsplash.com for a given criteria")

    def get_source_name(self):
        return "Unsplash"

    def get_server_options_key(self):
        return "unsplash_v2"

    def get_default_throttling(self):
        return Throttling(max_downloads_per_hour=20, max_queue_fills_per_hour=3)

    def on_image_set_as_wallpaper(self, img, meta):
        return UnsplashDownloader().on_image_set_as_wallpaper(img, meta)
