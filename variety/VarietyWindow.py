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

from AvgColor import AvgColor

class Color:
    RED = 1
    GREEN = 2
    BLUE = 3

# See variety_lib.Window.py for more details about how this class works
class VarietyWindow(Window):
    __gtype_name__ = "VarietyWindow"

    SCHEMA = 'org.gnome.desktop.background'
    KEY = 'picture-uri'

    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the main window"""
        super(VarietyWindow, self).finish_initializing(builder)

        self.gsettings = Gio.Settings.new(self.SCHEMA)

        self.AboutDialog = AboutVarietyDialog
        self.PreferencesDialog = PreferencesVarietyDialog

#        self.folder = "/usr/share/backgrounds/"
        self.folder = "/d/Pics/Wallpapers/"
        self.interval = 60
        self.avg_color = Color.RED

        self.used = []
        self.used.append(self.gsettings.get_string(self.KEY).replace("file://", ""))
        self.position = 0
        print(self.used)

    def set_wp(self, filename):
        self.gsettings.set_string(self.KEY, "file://" + filename)
        #self.gsettings.sync()
        self.gsettings.apply()

    def select_random_image(self, dirs):
        cnt = 0
        for dir in dirs:
            for root, subFolders, files in os.walk(dir):
                for filename in files:
                    if filename.lower().endswith(('.jpg', '.jpeg', '.gif', '.png')):
                        cnt += 1

        r = random.randint(0, cnt - 1)

        for dir in dirs:
            for root, subFolders, files in os.walk(dir):
                for filename in files:
                    if filename.lower().endswith(('.jpg', '.jpeg', '.gif', '.png')):
                        if r == 0:
                            return os.path.join(root, filename)
                        r -= 1
        # fallback - select some image if r never reaches 0 (can happen due to intermediate deletions)
        for dir in dirs:
            for root, subFolders, files in os.walk(dir):
                for filename in files:
                    if filename.lower().endswith(('.jpg', '.jpeg', '.gif', '.png')):
                        return os.path.join(root, filename)

    def on_indicator_scroll(self, indicator, steps, direction, data=None):
        # direction is 0 or 1
        if direction == 0:
            self.prev_wallpaper()
        else:
            self.next_wallpaper()

    def prev_wallpaper(self):
        if self.position >= len(self.used) - 1:
            return
        else:
            self.position += 1
            self.set_wp(self.used[self.position])

    def next_wallpaper(self):
        if self.position > 0:
            self.position -= 1
            self.set_wp(self.used[self.position])
        else:
            self.change_wallpaper()

    def change_wallpaper(self, widget=None, data=None):
        img = None
        for i in xrange(100):
            img = self.select_random_image([self.folder,])
            print("testing image ", img)
            if self.image_ok(img):
                print("ok")
                break
        if not img:
            img = self.select_random_image([self.folder, ])

        self.set_wp(img)
        self.used = self.used[self.position:]
        self.used.insert(0, img)
        self.position = 0
        if len(self.used) > 10:
            self.used = self.used[:10]
        print(self.used)

    def image_ok(self, img):
        return img != self.used[0] and self.avg_color_ok(img)

    def avg_color_ok(self, img):
        if not self.avg_color:
            return True
        avg = AvgColor(img)
        print avg.getAvg()
        r, g, b = avg.getAvg()
        tc = self.avg_color
        return tc == Color.RED and r > g + 50 and r > b + 50

