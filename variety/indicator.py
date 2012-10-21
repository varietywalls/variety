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

from variety_lib import varietyconfig

import gettext
from gettext import gettext as _
gettext.textdomain('variety')

class Indicator:
    def __init__(self, window):
        self.indicator = AppIndicator3.Indicator.new('variety', '', AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        icon_path = varietyconfig.get_data_file("media", "variety-indicator.svg")
        self.indicator.set_icon(icon_path)

        self.indicator.connect("scroll-event", window.on_indicator_scroll)

        #Uncomment and choose an icon for attention state.
        #self.indicator.set_attention_icon("ICON-NAME")

        self.menu = Gtk.Menu()

        self.file_label = Gtk.MenuItem(_("Current desktop wallpaper"))
        self.file_label.connect("activate", window.open_file)
        self.menu.append(self.file_label)

        self.show_origin = Gtk.MenuItem(_("Show origin"))
        self.show_origin.connect("activate", window.on_show_origin)
        self.show_origin.set_sensitive(False)
        self.menu.append(self.show_origin)

        self.menu.append(Gtk.SeparatorMenuItem.new())

        self.copy_to_favorites = Gtk.MenuItem(_("Copy to _Favorites"))
        self.copy_to_favorites.set_use_underline(True)
        self.copy_to_favorites.connect("activate", window.copy_to_favorites)
        self.menu.append(self.copy_to_favorites)

        self.move_to_favorites = Gtk.MenuItem(_("Move to Favorites"))
        self.move_to_favorites.set_use_underline(True)
        self.move_to_favorites.connect("activate", window.move_to_favorites)
        self.move_to_favorites.set_visible(False)
        self.menu.append(self.move_to_favorites)

        self.trash = Gtk.MenuItem(_("Delete to _Trash"))
        self.trash.set_use_underline(True)
        self.trash.connect("activate", window.move_to_trash)
        self.menu.append(self.trash)

#        self.open_file = Gtk.MenuItem(_("Open in Image Viewer"))
#        self.open_file.connect("activate", window.open_file)
#        self.menu.append(self.open_file)
#
#        self.open_folder = Gtk.MenuItem(_("Show Containing Folder"))
#        self.open_folder.connect("activate", window.open_folder)
#        self.menu.append(self.open_folder)

        self.focus = Gtk.MenuItem(_("Display Source"))
        self.focus.connect("activate", window.focus_in_preferences)
        self.menu.append(self.focus)

        self.publish_fb = Gtk.MenuItem(_("Share on Facebook"))
        self.publish_fb.connect("activate", window.publish_on_facebook)
        self.menu.append(self.publish_fb)

        self.menu.append(Gtk.SeparatorMenuItem.new())

        self.history = Gtk.CheckMenuItem(_("_History"))
        self.history.set_active(False)
        self.history.set_use_underline(True)
        self.history_handler_id = self.history.connect("toggled", window.show_hide_history)
        self.menu.append(self.history)

        self.downloads = Gtk.CheckMenuItem(_("Recent _Downloads"))
        self.downloads.set_active(False)
        self.downloads.set_use_underline(True)
        self.downloads_handler_id = self.downloads.connect("toggled", window.show_hide_downloads)
        self.menu.append(self.downloads)

        self.playback_menu = Gtk.Menu()

        self.prev = Gtk.MenuItem(_("_Previous"))
        self.prev.set_use_underline(True)
        self.prev.connect("activate", window.prev_wallpaper)
        self.playback_menu.append(self.prev)

        self.next = Gtk.MenuItem(_("_Next"))
        self.next.set_use_underline(True)
        self.next.connect("activate", window.next_wallpaper)
        self.playback_menu.append(self.next)

        self.fast_forward = Gtk.MenuItem(_("_Fast Forward"))
        self.fast_forward.set_use_underline(True)
        def _fast_forward(widget):
            window.next_wallpaper(widget, bypass_history=True)
        self.fast_forward.connect("activate", _fast_forward)
        self.playback_menu.append(self.fast_forward)

        self.playback_menu.append(Gtk.SeparatorMenuItem.new())

        self.pause_resume = Gtk.MenuItem(_("Pause"))
        self.pause_resume.connect("activate", window.on_pause_resume)
        self.playback_menu.append(self.pause_resume)

        self.playback_menu.append(Gtk.SeparatorMenuItem.new())
        self.scroll_tip = Gtk.MenuItem(_("Tip: Scroll wheel over icon\nfor Next and Previous"))
        self.scroll_tip.set_sensitive(False)
        self.playback_menu.append(self.scroll_tip)

        self.menu.append(Gtk.SeparatorMenuItem.new())

        self.playback = Gtk.MenuItem(_("_Playback"))
        self.playback.set_use_underline(True)
        self.playback.set_submenu(self.playback_menu)
        self.menu.append(self.playback)

        self.menu.append(Gtk.SeparatorMenuItem.new())

        #Adding preferences button
        self.preferences = Gtk.MenuItem(_("Preferences..."))
        self.preferences.connect("activate", window.on_mnu_preferences_activate)
        self.menu.append(self.preferences)

#        self.edit_config = Gtk.MenuItem("Edit config file...")
#        self.edit_config.connect("activate", window.edit_prefs_file)
#        self.menu.append(self.edit_config)

        self.about = Gtk.MenuItem(_("About"))
        self.about.connect("activate",window.on_mnu_about_activate)
        self.menu.append(self.about)

        self.quit = Gtk.MenuItem(_("Quit"))
        self.quit.connect("activate",window.on_quit)
        self.menu.append(self.quit)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

        window.ind = self

def new_application_indicator(window):
    ind = Indicator(window)
    return ind.indicator
