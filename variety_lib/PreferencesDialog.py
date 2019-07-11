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

"""this dialog adjusts values in gsettings
"""

import logging

from gi.repository import Gtk  # pylint: disable=E0611

from .helpers import get_builder, get_help_uri, show_uri

logger = logging.getLogger("variety_lib")


class PreferencesDialog(Gtk.Dialog):
    __gtype_name__ = "PreferencesDialog"

    def __new__(cls, parent):
        """Special static method that's automatically called by Python when 
        constructing a new instance of this class.
        
        Returns a fully instantiated PreferencesDialog object.
        """
        builder = get_builder("PreferencesVarietyDialog")
        new_object = builder.get_object("preferences_variety_dialog")
        new_object.finish_initializing(builder, parent)
        return new_object

    def finish_initializing(self, builder, parent):
        """Called while initializing this instance in __new__

        finish_initalizing should be called after parsing the ui definition
        and creating a PreferencesDialog object with it in order to
        finish initializing the start of the new PerferencesVarietyDialog
        instance.
        
        Put your initialization code in here and leave __init__ undefined.
        """

        # Get a reference to the builder and set up the signals.
        self.parent = parent
        self.builder = builder
        self.ui = builder.get_ui(self, True)

        # code for other initialization actions should be added here

    def on_btn_close_clicked(self, widget, data=None):
        self.hide()
        self.on_destroy()

    def on_btn_help_clicked(self, widget, data=None):
        show_uri(self, "ghelp:%s" % get_help_uri("preferences"))
