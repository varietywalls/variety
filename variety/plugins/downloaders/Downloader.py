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
    def __init__(self, source, description, folder_name, config=None, full_descriptor=None):
        super().__init__(source)
        self.source = source
        self.description = description
        self.folder_name = folder_name
        self.config = config
        self.full_descriptor = full_descriptor

        self._update_target_folder()

    def get_variety(self):
        return self.source.get_variety()

    def _update_target_folder(self):
        dl_folder = self.get_variety().options.real_download_folder
        filename = Util.convert_to_filename(self.folder_name)
        if len(filename) + len(dl_folder) > 160:
            filename = filename[:(150 - len(dl_folder))] + Util.md5(filename)[:10]
        self.target_folder = os.path.join(dl_folder, filename)

    def get_local_filename(self, url):
        return os.path.join(self.target_folder, Util.get_local_name(url))

    def get_source(self):
        """
        Returns the IImageSource associated with this downloader
        :return: IImageSource
        """
        return self.source

    def get_source_type(self):
        return self.source.get_source_type()

    def get_source_name(self):
        return self.source.get_source_name()

    def get_description(self):
        """
        User-friendly description of this downloader to show in UI (in the list of sources).
        E.g. "Downloads random images from site X", or "Images from Flickr user XXX"
        :return: description
        """
        return self.description

    def get_config(self):
        """
        Returns the config string used to create this downloader, e.g. "nature"
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
        return self.folder_name

    def get_refresh_interval_seconds(self):
        """
        Refresher downloaders can download one and the same image URL on a regular basis.
        Returning a positive integer here instructs Variety to initiate regular downloads and wallpaper changes
        when using this downloader.
        :return: None, or a positive number of seconds
        """
        return None

    @abc.abstractmethod
    def download_one(self):
        pass
