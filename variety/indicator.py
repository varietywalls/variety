#!/usr/bin/python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

"""Code to add AppIndicator."""

from gi.repository import Gtk # pylint: disable=E0611
from gi.repository import AppIndicator3 # pylint: disable=E0611

from variety_lib.helpers import get_media_file

import gettext
from gettext import gettext as _
gettext.textdomain('variety')

class Indicator:
    def __init__(self, window):
        self.indicator = AppIndicator3.Indicator.new('variety', '', AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        icon_uri = get_media_file("variety-indicator.svg")
        icon_path = icon_uri.replace("file:///", '')
        self.indicator.set_icon(icon_path)

        self.indicator.connect("scroll-event", window.on_indicator_scroll)

        #Uncomment and choose an icon for attention state. 
        #self.indicator.set_attention_icon("ICON-NAME")
        
        self.menu = Gtk.Menu()

        # Add items to Menu and connect signals.

        self.change = Gtk.MenuItem("Change wallpaper")
        self.change.connect("activate", window.change_wallpaper)
        self.change.show()
        self.menu.append(self.change)

        self.separator = Gtk.SeparatorMenuItem()
        self.separator.show()
        self.menu.append(self.separator)

        #Adding preferences button
        #window represents the main Window object of your app
        self.preferences = Gtk.MenuItem("Preferences...")
        self.preferences.connect("activate",window.on_mnu_preferences_activate)
        self.preferences.show()
        self.menu.append(self.preferences)

        self.about = Gtk.MenuItem("About")
        self.about.connect("activate",window.on_mnu_about_activate)
        self.about.show()
        self.menu.append(self.about)

        self.quit = Gtk.MenuItem("Quit")
        self.quit.connect("activate",window.on_mnu_close_activate)
        self.quit.show()
        self.menu.append(self.quit)

        # Add more items here                           

        self.menu.show()
        self.indicator.set_menu(self.menu)
    
def new_application_indicator(window):
    ind = Indicator(window)
    return ind.indicator
