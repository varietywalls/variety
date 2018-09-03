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


class IPlugin(object, metaclass=abc.ABCMeta):
    """
    The most simple interface to be inherited when creating a plugin.
    """

    @classmethod
    @abc.abstractmethod
    def get_info(cls):
        """
        Returns the basic info about the plugin. Please make sure the name is unique among all Variety plugins
        Format:
        return {
           "name": "Sample name",
           "description": "Sample description",
           "version": "1.0",
           "author": "Author name", # optional
           "url": "Plugin homepage URL"  # optional
        }
        """
        pass

    def __init__(self):
        """
        All plugins must have a default constructor with no parameters.
        Remember to call super.
        """
        self.active = False

        # These will be filled in by Jumble.load() and available before the first activate() call
        self.jumble = None
        self.path = None  # Path to the plugin python file
        self.folder = None  # Folder where plugin is located (can be used for loading UI resources, etc.).
        # This folder may be read-only. A separate config folder convention should be used to store config files.

    def activate(self):
        """
        Called at plugin activation. Please do not allocate large portions of memory or resources before this is called.
        Remember to call super first.
        This method can be called multiple times within a session.
        It may be called when the plugin is already active - in this case it should simply return.
        """
        if self.active:
            return
        self.active = True

    def deactivate(self):
        """
        Called when the plugin is disabled. Please free used memory and resources here.
        Remember to call super first.
        This method can be called multiple times within a session.
        It may be called when the plugin is already inactive - in this case it should simply return.
        """
        self.active = False

    def is_active(self):
        return self.active
