# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

import gettext
from gettext import gettext as _
gettext.textdomain('variety')

from gi.repository import Gtk # pylint: disable=E0611
import logging
logger = logging.getLogger('variety')

from variety_lib import Window
from variety.AboutVarietyDialog import AboutVarietyDialog
from variety.PreferencesVarietyDialog import PreferencesVarietyDialog

from gi.repository import Gio

import os
import random
random.seed()

# See variety_lib.Window.py for more details about how this class works
class VarietyWindow(Window):
    __gtype_name__ = "VarietyWindow"

    SCHEMA = 'org.gnome.desktop.background'
    KEY = 'picture-uri'

    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the main window"""
        super(VarietyWindow, self).finish_initializing(builder)

        self.AboutDialog = AboutVarietyDialog
        self.PreferencesDialog = PreferencesVarietyDialog

        self.folder = "/d/Pics/Wallpapers/"
        self.interval = 60

    def set_wp(self, filename):
        gsettings = Gio.Settings.new(self.SCHEMA)
        gsettings.set_string(self.KEY, "file://" + filename)
        gsettings.sync()

    def list_folder(self, dir):
        fileList = []
        for root, subFolders, files in os.walk(dir):
            for filename in files:
                if filename.lower().endswith(('.jpg', '.jpeg', '.gif', '.png')):
                    fileList.append(os.path.join(root, filename))
        return fileList

    def on_indicator_scroll(self, indicator, steps, direction, data=None):
        # direction is 0 or 1
        self.change_wallpaper()

    def change_wallpaper(self, widget=None, data=None):
        images = self.list_folder(self.folder)
        self.set_wp(images[random.randint(0, len(images) - 1)])

        # Code for other initialization actions should be added here.

