# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2012 Peter Levi <peterlevi@peterlevi.com>
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

# This is your preferences dialog.
#
# Define your preferences in
# data/glib-2.0/schemas/net.launchpad.variety.gschema.xml
# See http://developer.gnome.org/gio/stable/GSettings.html for more info.

from gi.repository import Gio, Gtk # pylint: disable=E0611

import gettext
from gettext import gettext as _
from variety.Options import Options
from variety.AddWallpapersNetCategoryDialog import AddWallpapersNetCategoryDialog

gettext.textdomain('variety')

import os
import logging
logger = logging.getLogger('variety')

from variety_lib.PreferencesDialog import PreferencesDialog

class PreferencesVarietyDialog(PreferencesDialog):
    __gtype_name__ = "PreferencesVarietyDialog"

    def finish_initializing(self, builder, parent): # pylint: disable=E1002
        """Set up the preferences dialog"""
        super(PreferencesVarietyDialog, self).finish_initializing(builder, parent)

        # Bind each preference widget to gsettings
#        widget = self.builder.get_object('example_entry')
#        settings.bind("example", widget, "text", Gio.SettingsBindFlags.DEFAULT)

        options = Options()
        options.read()

        self.ui.change_enabled.set_active(options.change_enabled)
        self.set_time(options.change_interval, self.ui.change_interval_text, self.ui.change_interval_time_unit)
        self.ui.change_on_start.set_active(options.change_on_start)

        self.ui.download_enabled.set_active(options.download_enabled)
        self.set_time(options.download_interval, self.ui.download_interval_text, self.ui.download_interval_time_unit)
        self.ui.download_folder_chooser.set_current_folder(os.path.expanduser(options.download_folder))
        self.ui.favorites_folder_chooser.set_current_folder(os.path.expanduser(options.favorites_folder))

        for s in options.sources:
            self.ui.sources.get_model().append([s[0], Options.type_to_str(s[1]), s[2]])
        self.ui.sources_enabled_checkbox_renderer.connect("toggled", self.source_enabled_toggled, self.ui.sources.get_model())

        for f in options.filters:
            cb = Gtk.CheckButton(f[1])
            cb.set_visible(True)
            cb.set_active(f[0])
            self.ui.filters_grid.add(cb)

    def source_enabled_toggled(self, widget, path, model):
        model[path][0] = not model[path][0]

    def set_time(self, interval, text, time_unit):
        if interval < 5:
            interval = 5
        times = [1, 60, 60 * 60, 24 * 60 * 60]
        x = len(times) - 1
        while times[x] > interval:
            x -= 1
        text.set_text(str(interval // times[x]))
        time_unit.set_active(x)
        return

    def on_add_images_clicked(self, widget=None):
        chooser = Gtk.FileChooserDialog("Add Images", parent=self, action=Gtk.FileChooserAction.OPEN,
            buttons=["Cancel", Gtk.ResponseType.CANCEL, "Add", Gtk.ResponseType.OK])
        chooser.set_select_multiple(True)
        chooser.set_local_only(True)
        filter = Gtk.FileFilter()
        filter.set_name("Images")
        for s in ["jpg", "jpeg", "png", "gif", "bmp", "tiff"]:
            filter.add_pattern("*." + s)
        chooser.add_filter(filter)
        response = chooser.run()

        if response == Gtk.ResponseType.OK:
            self.add_sources(Options.SourceType.IMAGE, chooser.get_filenames())

        chooser.destroy()

    def on_add_folders_clicked(self, widget=None):
        chooser = Gtk.FileChooserDialog("Add Folders - Only add the root folders, subfolders are searched recursively",
            parent=self, action=Gtk.FileChooserAction.SELECT_FOLDER,
            buttons=["Cancel", Gtk.ResponseType.CANCEL, "Add", Gtk.ResponseType.OK])
        chooser.set_select_multiple(True)
        chooser.set_local_only(True)
        response = chooser.run()

        if response == Gtk.ResponseType.OK:
            seld.add_sources(Options.SourceType.FOLDER, chooser.get_filenames())

        chooser.destroy()

    def add_sources(self, type, locations):
        existing = set()
        for r in self.ui.sources.get_model():
            if r[1] == Options.type_to_str(type):
                existing.add(r[2])
        for f in locations:
            if not f in existing:
                self.ui.sources.get_model().append([True, Options.type_to_str(type), f])

    def on_remove_sources_clicked(self, widget=None):
        model, rows = self.ui.sources.get_selection().get_selected_rows()
        # store the treeiters from paths
        iters = []
        for row in rows:
            iters.append(model.get_iter(row))
        # remove the rows (treeiters)
        for i in iters:
            if i is not None:
                model.remove(i)

    def on_add_wn_clicked(self, widget=None):
        dialog  = AddWallpapersNetCategoryDialog()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            url = dialog.ui.url.get_text().strip()
            if not url.startswith("http://"):
                url = "http://" + url
            if url.startswith("http://wallpapers.net"):
                self.add_sources(Options.SourceType.WN, [url])
        dialog.destroy()

