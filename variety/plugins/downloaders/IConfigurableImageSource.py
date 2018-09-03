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
from variety.plugins.downloaders.IImageSource import IImageSource


class IConfigurableImageSource(IImageSource, metaclass=abc.ABCMeta):
    def __init__(self, source_type):
        super().__init__(source_type)

    @abc.abstractmethod
    def search(self, config):
        pass

    @abc.abstractmethod
    def create_downloader(self, config, full_descriptor=None):
        pass

    @abc.abstractmethod
    def get_ui_config_help_string(self):
        pass

