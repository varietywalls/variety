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
import os

from variety.Util import Util


class Downloader(abc.ABC):
    def __init__(self, source, config=None, full_descriptor=None):
        """
        Create a downloader for an image source
        :param source: the image source this downloader is associated with
        :param config: optional, see get_config()
        :param full_descriptor: optional, see get_full_descriptor()
        """
        super().__init__()
        self.source = source
        self.config = config
        self.full_descriptor = full_descriptor
        self.target_folder = None  # initialized post construction by update_download_folder

    def get_variety(self):
        """
        :return: the VarietyWindow instance, if set in the source, else None
        """
        return self.source.get_variety()

    def update_download_folder(self, global_download_folder):
        """
        Called after initialization, once the VarietyWindow instance is filled in, sets
        the target folder according to the current options. Also called if downloads folder
        is changed in settings.
        :param global_download_folder the "global" download folder as set in Variety's preferences
        Our target_folder will be a subfolder to that one, named depending on what get_folder_name()
        returns.
        :return the target_folder for this particular downloader
        """
        filename = self.get_folder_name()
        if len(filename) + len(global_download_folder) > 160:
            filename = filename[:(150 - len(global_download_folder))] + Util.md5(filename)[:10]
        self.target_folder = os.path.join(global_download_folder, filename)
        return self.target_folder

    def get_local_filename(self, url):
        """
        Returns the local file path where to save a remote image (at URL url)
        :param url: the URL of the image
        :return: the full local path, under the current target_folder
        """
        if self.target_folder is None:
            raise Exception('update_download_folder was not called before downloading')
        return os.path.join(self.target_folder, Util.get_local_name(url))

    def get_source(self):
        """
        Returns the IImageSource associated with this downloader
        :return: IImageSource
        """
        return self.source

    def get_source_type(self):
        """
        :return: the image source's source type
        """
        return self.source.get_source_type()

    def get_source_name(self):
        """
        :return: the image source's source name
        """
        return self.source.get_source_name()

    def get_source_location(self):
        """
        What to save as sourceLocation in the images' metadata.
        By default this is this downloader's config string.
        Override in SimpleDownloaders to return a non-null string.
        :return: the source location to be saved in images
        """
        return self.get_config()

    @abc.abstractmethod
    def get_description(self):
        """
        User-friendly description of this downloader to show in UI (in the list of sources).
        E.g. "Downloads random images from site X", or "Images from Flickr user XXX"
        :return: description
        """
        pass

    def get_config(self):
        """
        Returns the config string used to create this downloader, e.g. a search keyword, or URL
        :return: the config string, will be None for non-configurable sources
        """
        return self.config

    def get_full_descriptor(self):
        """
        Returns a dict object that will be persisted and loaded along with the config string.
        This allows the downloader to cache information associated with the config without having
        to make http calls every time it is loaded.
        E.g. this could be the user ID of the Flickr user associated with the config string.
        :return:
        """
        return self.full_descriptor

    def get_folder_name(self):
        """
        How should the folder be named where images from this source are downloaded to
        :return: folder name (just name, not full path)
        """
        if self.config:
            return self.get_source_type() + '_' + Util.convert_to_filename(self.config)
        else:
            return self.get_source_name()

    def get_refresh_interval_seconds(self):
        """
        Refresher downloaders can download one and the same image URL on a regular basis.
        Returning a positive integer here instructs Variety to initiate regular downloads and
        wallpaper changes when using this downloader.
        Images downloaded by refreshers MUST contain the string "--refreshable" in the name -
        this is the way Variety will know these images can be set as wallpaper again and again.
        :return: False by defualt, override to return True when implementing refreshers
        :return: None, or a positive number of seconds
        """
        return None

    def is_refresher(self):
        """
        Checks if this is a "refresher" plugin, i.e. refresh_interval_seconds is not None
        """
        return self.get_refresh_interval_seconds() is not None

    @abc.abstractmethod
    def download_one(self):
        """
        Downloads a single image. DefaultDownloader provides a reference implementation and most
        plugins should inherit DefaultDownloader instead of implementing this method.
        :return: the downloaded file path, or None
        """
        pass
