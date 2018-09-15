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
from variety.plugins.IVarietyPlugin import IVarietyPlugin

logger = logging.getLogger('variety')


Throttling = collections.namedtuple('Throttling', ['min_download_interval', 'min_fill_queue_interval'])


class ImageSource(IVarietyPlugin, metaclass=abc.ABCMeta):
    def __init__(self, source_type):
        super().__init__()
        self.source_type = source_type
        self.last_download_time = 0
        self.last_fill_time = 0

    def get_variety(self):
        return self.jumble.parent

    def get_source_type(self):
        """
        Returns a key for this source that will be used to identify it in
        configuration files, and will be saved in image metadata under Xmp.variety.sourceType.
        Variety will use this source type to find which plugin can handle a particular
        saved image source configuration, so this should not collide between different image
        source plugins.
        :return: source type, e.g. "flickr", "unsplash", etc.
        """
        return self.source_type

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
        Called when a wallpaper downloaded from this source was copied to favorites.
        This can be used to call back the image provider for stats purposes.
        :param img path to the image file
        :param meta image metadata
        """
        pass

    def get_default_throttling(self):
        """
        Throttling serves to avoid overloading servers when multiple Variety users use the source simultaneously.
        It is normally controlled via a remote config, but defaults should be provided for the cases
        when the remote config is not set or cannot be fetched.
        All downloaders for the same source are throttled together.
        :return: a dict with min_download_interval (in seconds) and min_fill_queue_interval (in seconds)
        """
        return Throttling(min_download_interval=0, min_fill_queue_interval=0)

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

        min_download_interval, min_fill_queue_interval = defaults
        name = self.get_source_name()

        try:
            logger.info(lambda: "%s: parsing serverside options" % name)
            options = self.get_server_options()
            logger.info(lambda: "%s serverside options: %s" % (self.get_source_name(), str(options)))
        except Exception:
            logger.exception(lambda: "Could not parse %s serverside options, using defaults %d, %d" % (
                name, min_download_interval, min_fill_queue_interval))
            return defaults

        try:
            min_download_interval = int(options["min_download_interval"])
        except Exception:
            logger.exception(lambda: "Bad or missing min_download_interval")

        try:
            min_fill_queue_interval = int(options["min_fill_queue_interval"])
        except Exception:
            logger.exception(lambda: "Bad or missing min_fill_queue_interval")

        return Throttling(min_download_interval, min_fill_queue_interval)
