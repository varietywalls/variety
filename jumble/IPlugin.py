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

class IPlugin(object):
    """
    The most simple interface to be inherited when creating a plugin.
    """
    @classmethod
    def get_info(cls):
        return {}
#        return {
#            "name": None,
#            "description": None,
#            "version": None,
#            "author": None,
#            "url": None
#        }

    def __init__(self):
        self.is_activated = False

        # These will be filled in by Jumble
        self.jumble = None
        self.path = None        # path to the plugin python file
        self.folder = None      # folder where plugin is located (can be used for loading UI resources, etc.)

    def activate(self):
        """
       Called at plugin activation.
       """
        self.is_activated = True

    def deactivate(self):
        """
       Called when the plugin is disabled.
       """
        self.is_activated = False

