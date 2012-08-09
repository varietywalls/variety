# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Peter Levi <peterlevi@peterlevi.com>
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


        self.file_label = Gtk.MenuItem("Current desktop wallpaper")
        self.file_label.connect("activate", window.open_file)
        self.menu.append(self.file_label)

        self.show_origin = Gtk.MenuItem("Show origin")
        self.show_origin.connect("activate", window.on_show_origin)
        self.show_origin.set_sensitive(False)
        self.menu.append(self.show_origin)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.prev = Gtk.MenuItem("_Previous")
        self.prev.set_use_underline(True)
        self.prev.connect("activate", window.prev_wallpaper)
        self.menu.append(self.prev)

        self.next = Gtk.MenuItem("_Next")
        self.next.set_use_underline(True)
        self.next.connect("activate", window.next_wallpaper)
        self.menu.append(self.next)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.pause_resume = Gtk.MenuItem("Pause")
        self.pause_resume.connect("activate", window.on_pause_resume)
        self.menu.append(self.pause_resume)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.history = Gtk.MenuItem("Show _History")
        self.history.set_use_underline(True)
        self.history.connect("activate", window.show_hide_history)
        self.menu.append(self.history)

        self.menu.append(Gtk.SeparatorMenuItem())

        self.open_file = Gtk.MenuItem("Open in Image Viewer")
        self.open_file.connect("activate", window.open_file)
        self.menu.append(self.open_file)

        self.open_folder = Gtk.MenuItem("Show Containing Folder")
        self.open_folder.connect("activate", window.open_folder)
        self.menu.append(self.open_folder)

        self.trash = Gtk.MenuItem("Move to _Trash")
        self.trash.set_use_underline(True)
        self.trash.connect("activate", window.move_to_trash)
        self.menu.append(self.trash)

        self.favorite = Gtk.MenuItem("Copy to _Favorites")
        self.favorite.set_use_underline(True)
        self.favorite.connect("activate", window.copy_to_favorites)
        self.menu.append(self.favorite)

        self.menu.append(Gtk.SeparatorMenuItem())

        #Adding preferences button
        self.preferences = Gtk.MenuItem("Preferences...")
        self.preferences.connect("activate", window.on_mnu_preferences_activate)
        self.menu.append(self.preferences)

#        self.edit_config = Gtk.MenuItem("Edit config file...")
#        self.edit_config.connect("activate", window.edit_prefs_file)
#        self.menu.append(self.edit_config)

        self.about = Gtk.MenuItem("About")
        self.about.connect("activate",window.on_mnu_about_activate)
        self.menu.append(self.about)

        self.quit = Gtk.MenuItem("Quit")
        self.quit.connect("activate",window.on_quit)
        self.menu.append(self.quit)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        window.ind = self

def new_application_indicator(window):
    ind = Indicator(window)
    return ind.indicator
