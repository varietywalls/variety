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

from variety.plugins.downloaders.ImageSource import ImageSource


class ConfigurableImageSource(ImageSource, metaclass=abc.ABCMeta):
    """
    Implements searchable image sources.
    TODO: This plugin type is still in ideation phase, WIP.
    """

    @abc.abstractmethod
    def validate(self, config):
        """
        Example valid: return formatted(query), None
        Example invalid: return query, _('Not a proper XYZ query')
        """
        # TODO allow also returning full_descriptor, propagete all the way to persisted source tuple
        pass

    @abc.abstractmethod
    def create_downloader(self, config, full_descriptor=None):
        pass

    @abc.abstractmethod
    def get_ui_instruction(self):
        pass

    @abc.abstractmethod
    def get_ui_short_instruction(self):
        pass

    @abc.abstractmethod
    def get_ui_short_description(self):
        pass
