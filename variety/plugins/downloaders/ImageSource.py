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
import abc
import collections
import logging
import time
from datetime import timedelta

from variety.plugins.IVarietyPlugin import IVarietyPlugin

logger = logging.getLogger("variety")


Throttling = collections.namedtuple(
    "Throttling", ["max_downloads_per_hour", "max_queue_fills_per_hour"]
)


class ImageSource(IVarietyPlugin, metaclass=abc.ABCMeta):
    def __init__(self):
        super().__init__()
        self._last_download_times = []
        self._last_queue_fill_times = []
        self.variety = None

    def set_variety(self, variety):
        """
        Sets the VarietyWindow instance. This is called after Jumble creates the instance, before
        it is actually used.
        :param variety: the instance of VarietyWindow
        """
        self.variety = variety

    def get_variety(self):
        """
        Returns the VarietyWindow instance, if set via set_variety(), or None.
        This is available before the source is actually used.
        :return the instance of VarietyWindow
        """
        return self.variety

    @abc.abstractmethod
    def get_source_type(self):
        """
        Returns a key for this source that will be used to identify it in
        configuration files, and will be saved in image metadata under Xmp.variety.sourceType.
        Variety will use this source type to find which plugin can handle a particular
        saved image source configuration, so this should not collide between different image
        source plugins.
        :return: source type, e.g. "flickr", "unsplash", etc.
        """
        pass

    def get_source_name(self):
        """
        Returns the value that will go into Xmp.variety.sourceName in image metadata.
        This will also be shown in UI.
        This could be the name of the service that is used to fetch images, e.g. Flickr.
        Default implementation is to return source_type, with uppercase first letter.
        :return: source name, e.g. "Flickr", "Unsplash", etc.
        """
        source_type = self.get_source_type()
        return source_type[0].upper() + source_type[1:]

    def on_image_set_as_wallpaper(self, img, meta):
        """
        Called when a wallpaper downloaded from this source was used as a wallpaper.
        This can be used to call back the image provider for stats purposes.
        :param img path to the image file
        :param meta image metadata
        """
        pass

    def on_image_favorited(self, img, meta):
        """
        Called when a wallpaper downloaded from this source was copied or moved to favorites.
        This can be used to call back the image provider for stats purposes.
        :param img path to the image file
        :param meta image metadata
        """
        pass

    def get_default_throttling(self):
        """
        Throttling serves to avoid overloading servers when multiple Variety users use the source 
        simultaneously. It is normally controlled via a remote config, but defaults should be 
        provided for the cases when the remote config is not set or cannot be fetched.
        All downloaders for the same source are throttled together.
        :return: a Throttling namedtuple
        """
        return Throttling(max_downloads_per_hour=None, max_queue_fills_per_hour=None)

    def get_server_options_key(self):
        """
        Key under the the server-side throttling options where the configs for this source reside.
        By default it is the same as the source type.
        :return: key in remote server options for this source, e.g. "unsplash_v2"
        """
        return self.get_source_type()

    def get_server_options(self):
        """
        Returns the server options for this source.
        The default implementation reads from get_variety().server_options, i.e. it uses Variety's central
        serverside options, but you could override this method to read from elsewhere.
        :return: remotely-configured options for this image source
        """
        return self.get_variety().server_options[self.get_server_options_key()]

    def get_throttling(self):
        """
        Returns the actual throttling, taking remote configuration into account (if available)
        """
        defaults = self.get_default_throttling()

        max_downloads_per_hour, max_queue_fills_per_hour = defaults
        name = self.get_source_name()

        try:
            logger.info(lambda: "{}: parsing serverside options".format(name))
            options = self.get_server_options()
            logger.info(
                lambda: "{} serverside options: {}".format(self.get_source_name(), str(options))
            )
        except Exception:
            logger.info(
                lambda: "Could not parse {} serverside options, using defaults {}, {}".format(
                    name, max_downloads_per_hour, max_queue_fills_per_hour
                )
            )
            return defaults

        try:
            max_downloads_per_hour = int(options["max_downloads_per_hour"])
        except Exception:
            pass

        try:
            max_queue_fills_per_hour = int(options["max_queue_fills_per_hour"])
        except Exception:
            pass

        return Throttling(max_downloads_per_hour, max_queue_fills_per_hour)

    def _count_last_hour_downloads(self):
        now = time.time()
        self._last_download_times = [t for t in self._last_download_times if now - t < 3600]
        return len(self._last_download_times)

    def is_download_allowed(self):
        max_downloads_per_hour, _ = self.get_throttling()
        return (
            max_downloads_per_hour is None
            or self._count_last_hour_downloads() < max_downloads_per_hour
        )

    def register_download(self):
        self._last_download_times.append(time.time())

    def _count_last_hour_queue_fills(self):
        now = time.time()
        self._last_queue_fill_times = [t for t in self._last_queue_fill_times if now - t < 3600]
        return len(self._last_queue_fill_times)

    def is_fill_queue_allowed(self):
        _, max_queue_fills_per_hour = self.get_throttling()
        return (
            max_queue_fills_per_hour is None
            or self._count_last_hour_queue_fills() < max_queue_fills_per_hour
        )

    def register_fill_queue(self):
        self._last_queue_fill_times.append(time.time())
