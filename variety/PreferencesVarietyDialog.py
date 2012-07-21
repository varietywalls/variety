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

# This is your preferences dialog.
#
# Define your preferences in
# data/glib-2.0/schemas/net.launchpad.variety.gschema.xml
# See http://developer.gnome.org/gio/stable/GSettings.html for more info.

from gi.repository import Gio, Gtk, Gdk # pylint: disable=E0611

import gettext
from gettext import gettext as _
from variety.AddWallbaseDialog import AddWallbaseDialog

from variety.Options import Options
from variety.AddWallpapersNetCategoryDialog import AddWallpapersNetCategoryDialog
from variety.AddFlickrDialog import AddFlickrDialog

gettext.textdomain('variety')

import os
import logging

logger = logging.getLogger('variety')

from variety_lib.PreferencesDialog import PreferencesDialog

UNREMOVEABLE_TYPES = [Options.SourceType.FAVORITES, Options.SourceType.DESKTOPPR, Options.SourceType.APOD]

class PreferencesVarietyDialog(PreferencesDialog):
    __gtype_name__ = "PreferencesVarietyDialog"

    def finish_initializing(self, builder, parent): # pylint: disable=E1002
        """Set up the preferences dialog"""
        super(PreferencesVarietyDialog, self).finish_initializing(builder, parent)

        # Bind each preference widget to gsettings
        #        widget = self.builder.get_object('example_entry')
        #        settings.bind("example", widget, "text", Gio.SettingsBindFlags.DEFAULT)

        self.options = Options()
        self.options.read()

        self.ui.autostart.set_active(os.path.isfile(os.path.expanduser("~/.config/autostart/variety.desktop")))

        self.ui.change_enabled.set_active(self.options.change_enabled)
        self.set_time(self.options.change_interval, self.ui.change_interval_text, self.ui.change_interval_time_unit)
        self.ui.change_on_start.set_active(self.options.change_on_start)

        self.ui.download_enabled.set_active(self.options.download_enabled)
        self.set_time(self.options.download_interval, self.ui.download_interval_text,
            self.ui.download_interval_time_unit)

        self.ui.download_folder_chooser.set_filename(os.path.expanduser(self.options.download_folder))

        self.ui.quota_enabled.set_active(self.options.quota_enabled)
        self.ui.quota_size.set_text(str(self.options.quota_size))

        self.ui.favorites_folder_chooser.set_filename(os.path.expanduser(self.options.favorites_folder))

        self.ui.desired_color_enabled.set_active(self.options.desired_color_enabled)
        self.ui.desired_color.set_color(Gdk.Color(red = 160 * 256, green = 160 * 256, blue = 160 * 256))
        c = self.options.desired_color
        if c:
            self.ui.desired_color.set_color(Gdk.Color(red = c[0] * 256, green = c[1] * 256, blue = c[2] * 256))

        self.ui.min_size_enabled.set_active(self.options.min_size_enabled)
        min_sizes = [50, 80, 100]
        index = 0
        while min_sizes[index] < self.options.min_size and index < len(min_sizes) - 1:
            index += 1
        self.ui.min_size.set_active(index)
        self.ui.landscape_enabled.set_active(self.options.use_landscape_enabled)
        self.ui.lightness_enabled.set_active(self.options.lightness_enabled)
        self.ui.lightness.set_active(0 if self.options.lightness_mode == Options.LightnessMode.DARK else 1)


        for s in self.options.sources:
            self.ui.sources.get_model().append([s[0], Options.type_to_str(s[1]), s[2]])
        self.ui.sources_enabled_checkbox_renderer.connect("toggled", self.source_enabled_toggled,
            self.ui.sources.get_model())
        #self.ui.sources.get_selection().connect("changed", self.on_sources_selection_changed)

        self.filter_checkboxes = []
        for i, f in enumerate(self.options.filters):
            cb = Gtk.CheckButton(f[1])
            cb.set_visible(True)
            cb.set_active(f[0])
            cb.set_margin_right(30)
            self.ui.filters_grid.add(cb)
            self.filter_checkboxes.append(cb)

        self.on_change_enabled_toggled()
        self.on_download_enabled_toggled()
        self.on_sources_selection_changed()
        self.on_desired_color_enabled_toggled()
        self.on_min_size_enabled_toggled()
        self.on_lightness_enabled_toggled()

        self.dialog = None

    def source_enabled_toggled(self, widget, path, model):
        model[path][0] = not model[path][0]
        if model[path][0] and model[path][1] == Options.type_to_str(Options.SourceType.DESKTOPPR):
            dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
                Gtk.MessageType.INFO, Gtk.ButtonsType.OK,
                "CONTAINS PORN!\n\nYou just enabled downloading from Desktoppr. Please be warned that as of July 2012 "
                "Desktoppr contains a small portion of nudity and porn images that are sometimes returned by their "
                "random wallpaper API, and thus may appear on your desktop.")
            dialog.set_title("Desktoppr - NSFW Warning")
            self.parent.dialogs.append(dialog)
            dialog.run()
            dialog.destroy()
            self.parent.dialogs.remove(dialog)


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

    def read_time(self, text_entry, time_unit_combo, minimum, default):
        result = default
        try:
            interval = int(text_entry.get_text())
            tree_iter = time_unit_combo.get_active_iter()
            if tree_iter:
                model = time_unit_combo.get_model()
                time_unit_seconds = model[tree_iter][1]
                result = interval * time_unit_seconds
                if result < minimum:
                    result = minimum
        except Exception:
            logger.exception("Could not understand interval")
        return result

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
            self.add_sources(Options.SourceType.FOLDER, chooser.get_filenames())

        chooser.destroy()

    def add_sources(self, type, locations):
        self.ui.sources.get_selection().unselect_all()
        existing = {}
        for i, r in enumerate(self.ui.sources.get_model()):
            if r[1] == Options.type_to_str(type):
                if type == Options.SourceType.FOLDER:
                    existing[os.path.normpath(r[2])] = r, i
                else:
                    existing[r[2]] = r, i

        for f in locations:
            if type == Options.SourceType.FOLDER:
                f = os.path.normpath(f)
            if not f in existing:
                self.ui.sources.get_model().append([True, Options.type_to_str(type), f])
                self.ui.sources.get_selection().select_path(len(self.ui.sources.get_model()) - 1)
            else:
                logger.info("Source already exists, activating it: " + f)
                existing[f][0][0] = True
                self.ui.sources.get_selection().select_path(existing[f][1])

    def on_remove_sources_clicked(self, widget=None):
        model, rows = self.ui.sources.get_selection().get_selected_rows()
        # store the treeiters from paths
        iters = []
        for row in rows:
            if Options.str_to_type(model[row][1]) not in UNREMOVEABLE_TYPES:
                iters.append(model.get_iter(row))
        # remove the rows (treeiters)
        for i in iters:
            if i is not None:
                model.remove(i)

    def on_sources_selection_changed(self, widget=None):
        model, rows = self.ui.sources.get_selection().get_selected_rows()
        for row in rows:
            if Options.str_to_type(model[row][1]) in UNREMOVEABLE_TYPES:
                self.ui.remove_sources.set_sensitive(False)
                return

        self.ui.remove_sources.set_sensitive(len(rows) > 0)

    def on_add_wn_clicked(self, widget=None):
        self.dialog = AddWallpapersNetCategoryDialog()
        self.dialog.parent = self
        self.dialog.set_transient_for(self)
        self.dialog.run()

    def on_add_flickr_clicked(self, widget=None):
        self.dialog = AddFlickrDialog()
        self.dialog.parent = self
        self.dialog.set_transient_for(self)
        self.dialog.run()

    def on_add_wallbase_clicked(self, widget=None):
        self.dialog = AddWallbaseDialog()
        self.dialog.parent = self
        self.dialog.set_transient_for(self)
        self.dialog.run()

    def on_wn_dialog_okay(self, url):
        self.add_sources(Options.SourceType.WN, [url])
        self.dialog = None

    def on_flickr_dialog_okay(self, flickr_search):
        self.add_sources(Options.SourceType.FLICKR, [flickr_search])
        self.dialog = None

    def on_wallbase_dialog_okay(self, wallbase_search):
        self.add_sources(Options.SourceType.WALLBASE, [wallbase_search])
        self.dialog = None

    def on_cancel_clicked(self, widget):
        self.destroy()

    def on_save_clicked(self, widget):
        try:
            self.options.change_enabled = self.ui.change_enabled.get_active()
            self.options.change_on_start = self.ui.change_on_start.get_active()
            self.options.change_interval = self.read_time(
                self.ui.change_interval_text, self.ui.change_interval_time_unit, 5, self.options.change_interval)

            self.options.download_enabled = self.ui.download_enabled.get_active()
            self.options.download_interval = self.read_time(
                self.ui.download_interval_text, self.ui.download_interval_time_unit, 30, self.options.download_interval)

            self.options.quota_enabled = self.ui.quota_enabled.get_active()
            try:
                self.options.quota_size = int(self.ui.quota_size.get_text())
                if self.options.quota_size < 50:
                    self.options.quota_size = 50
            except Exception:
                logger.exception("Could not understand quota size")

            if os.access(self.ui.download_folder_chooser.get_filename(), os.W_OK):
                self.options.download_folder = self.ui.download_folder_chooser.get_filename()
            if os.access(self.ui.favorites_folder_chooser.get_filename(), os.W_OK):
                self.options.favorites_folder = self.ui.favorites_folder_chooser.get_filename()

            self.options.sources = []
            for r in self.ui.sources.get_model():
                self.options.sources.append([r[0], Options.str_to_type(r[1]), r[2]])

            self.options.desired_color_enabled = self.ui.desired_color_enabled.get_active()
            c = self.ui.desired_color.get_color()
            self.options.desired_color = (c.red // 256, c.green // 256, c.blue // 256)

            self.options.min_size_enabled = self.ui.min_size_enabled.get_active()
            try:
                self.options.min_size = int(self.ui.min_size.get_active_text())
            except Exception:
                pass

            self.options.use_landscape_enabled = self.ui.landscape_enabled.get_active()

            self.options.lightness_enabled = self.ui.lightness_enabled.get_active()
            self.options.lightness_mode = \
                Options.LightnessMode.DARK if self.ui.lightness.get_active() == 0 else Options.LightnessMode.LIGHT

            enabled_filters = [cb.get_label().lower() for cb in self.filter_checkboxes if cb.get_active()]
            for f in self.options.filters:
                f[0] = f[1].lower() in enabled_filters

            self.options.write()
            self.parent.reload_config()
            self.parent.update_pause_resume()

            self.update_autostart()

            self.destroy()
        except Exception:
            logger.exception("Error while saving")
            dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
                Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                "An error occurred while saving preferences.\n"
                "Please run from a terminal with the -v flag and try again.")
            dialog.set_title("Oops")
            dialog.run()
            dialog.destroy()

    def update_autostart(self):
        try:
            content = (
                "[Desktop Entry]\n"
                "Name=Variety\n"
                "Comment=Variety Wallpaper Changer\n"
                "Icon=%s\n"
                "Exec=%s\n"
                "Terminal=false\n"
                "Type=Application\n")

            file = os.path.expanduser("~/.config/autostart/variety.desktop")

            if not self.ui.autostart.get_active():
                try:
                    if os.path.exists(file):
                        logger.info("Removing autostart entry")
                        os.unlink(file)
                except Exception:
                    logger.exception("Could not remove autostart entry variety.desktop")
            else:
                if not os.path.exists(file):
                    logger.info("Creating autostart entry")
                    with open("/proc/%s/cmdline" % os.getpid()) as f:
                        cmdline = f.read().strip()

                    if cmdline.find("/opt/extras") >= 0:
                        content = content % (
                                  "/opt/extras.ubuntu.com/variety/share/variety/media/variety.svg",
                                  "/opt/extras.ubuntu.com/variety/bin/variety")
                    elif cmdline.find("/opt/") >= 0:
                        content = content % (
                                  "/opt/variety/share/variety/media/variety.svg",
                                  "/opt/variety/bin/variety")
                    else:
                        content = content % (
                                  "/usr/share/variety/media/variety.svg",
                                  "/usr/bin/variety")

                    with open(file, "w") as desktop_file:
                        desktop_file.write(content)
        except Exception, e:
            logger.exception("Error while creating autostart desktop entry")
            dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
                Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                "An error occurred while creating the autostart desktop entry\n"
                "Please run from a terminal with the -v flag and try again.")
            dialog.set_title("Oops")
            dialog.run()
            dialog.destroy()


    def on_change_enabled_toggled(self, widget = None):
        self.ui.change_interval_text.set_sensitive(self.ui.change_enabled.get_active())
        self.ui.change_interval_time_unit.set_sensitive(self.ui.change_enabled.get_active())

    def on_download_enabled_toggled(self, widget = None):
        active = self.ui.download_enabled.get_active()
        self.ui.download_interval_text.set_sensitive(active)
        self.ui.download_interval_time_unit.set_sensitive(active)
        self.ui.download_folder_chooser.set_sensitive(active)
        self.ui.quota_enabled.set_sensitive(active)
        self.ui.quota_size.set_sensitive(active)
        self.on_quota_enabled_toggled()

    def on_quota_enabled_toggled(self, widget = None):
        active = self.ui.download_enabled.get_active() and self.ui.quota_enabled.get_active()
        self.ui.quota_size.set_sensitive(active)
        self.ui.quota_label.set_sensitive(active)

    def on_desired_color_enabled_toggled(self, widget = None):
        self.ui.desired_color.set_sensitive(self.ui.desired_color_enabled.get_active())

    def on_min_size_enabled_toggled(self, widget = None):
        self.ui.min_size.set_sensitive(self.ui.min_size_enabled.get_active())
        self.ui.min_size_label.set_sensitive(self.ui.min_size_enabled.get_active())

    def on_lightness_enabled_toggled(self, widget = None):
        self.ui.lightness.set_sensitive(self.ui.lightness_enabled.get_active())

    def on_destroy(self, widget = None):
        if self.dialog:
            self.dialog.destroy()

    def on_downloaded_changed(self, widget=None):
        if not os.access(self.ui.download_folder_chooser.get_filename(), os.W_OK):
            self.ui.error_downloaded.set_label("No write permissions")
        else:
            self.ui.error_downloaded.set_label("")

    def on_favorites_changed(self, widget=None):
        if not os.access(self.ui.favorites_folder_chooser.get_filename(), os.W_OK):
            self.ui.error_favorites.set_label("No write permissions")
        else:
            self.ui.error_downloaded.set_label("")
