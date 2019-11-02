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
    Implements configurable/searchable image sources.
    """

    @abc.abstractmethod
    def validate(self, config):
        """
        Given a source config, validates whether images can be fetche for this config.
        As part of the validation, performs config normalization and initial lookup calls and
        returns a "final" config that will be persisted.

        Returns a tuple (config_to_persist, error_message)
        If error_message is None, the config is considered valid and a source is added.
        If error_message is not None, it is shown as an error in UI and a new source is not added.
        Example valid: return formatted(query), None
        Example invalid: return query, _('Not a proper XYZ query')
        @:param config the search query, URL or other config string for the new source
        @:return tuple (config_to_persist, error_message_or_none)
        """
        pass

    @abc.abstractmethod
    def create_downloader(self, config):
        """
        Creates a Downloader for the given config
        :param config: the downloader config
        :return: a Downloader object
        """
        pass

    @abc.abstractmethod
    def get_ui_instruction(self):
        """
        Long instruction to show in the "Add..." dialog
        :return: long instruction
        """
        pass

    @abc.abstractmethod
    def get_ui_short_instruction(self):
        """
        Short instructiton to show in the "Add..." dialog in front of the input field
        :return: short instruction
        """
        pass

    @abc.abstractmethod
    def get_ui_short_description(self):
        """
        Source description to show in the "Add..." menu popup
        :return: short description
        """
        pass
