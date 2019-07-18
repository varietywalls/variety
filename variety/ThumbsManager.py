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

import logging
import os
import threading
import webbrowser

from gi.repository import Gdk, GdkPixbuf, GObject, Gtk

from configobj import ConfigObj
from variety.ThumbsWindow import ThumbsWindow
from variety.Util import Util, _
from variety_lib import varietyconfig

logger = logging.getLogger("variety")


class ThumbsManager:
    POSITIONS = {
        "bottom": ThumbsWindow.BOTTOM,
        "top": ThumbsWindow.TOP,
        "left": ThumbsWindow.LEFT,
        "right": ThumbsWindow.RIGHT,
    }

    POSITION_NAMES = {
        "bottom": _("Bottom"),
        "top": _("Top"),
        "left": _("Left"),
        "right": _("Right"),
    }

    R_POSITIONS = {v: k for (k, v) in POSITIONS.items()}

    SIZES = [x * 30 for x in range(2, 11)]

    UNLIMITED = "Unlimited"

    LIMITS = [10, 50, 100, 200, 500, 1000, 2000, UNLIMITED]

    class Options:
        def __init__(self):
            self.position = ThumbsWindow.BOTTOM
            self.breadth = 120
            self.limit = 200

    def __init__(self, parent):
        self.parent = parent
        self.thumbs_window = None
        self.show_thumbs_lock = threading.Lock()

        self.pinned = False
        self.images = []
        self.screen = None

        self.type = None
        self.folders = None

        self.active_file = None
        self.active_position = None

    def create_menu(self, file):
        options = self.load_options()

        menu = Gtk.Menu()

        position_menu = Gtk.Menu()
        for p, v in ThumbsManager.POSITIONS.items():
            item = Gtk.CheckMenuItem(ThumbsManager.POSITION_NAMES[p])
            item.set_draw_as_radio(True)
            item.set_active(options.position == v)

            def _set_position(widget, pos=p):
                self.set_position(pos)

            item.connect("activate", _set_position)
            position_menu.append(item)

        size_menu = Gtk.Menu()
        for size in ThumbsManager.SIZES:
            item = Gtk.CheckMenuItem(str(size))
            item.set_draw_as_radio(True)
            item.set_active(options.breadth == size)

            def _set_size(widget, size=size):
                self.set_size(size)

            item.connect("activate", _set_size)
            size_menu.append(item)

        limit_menu = Gtk.Menu()
        for limit in ThumbsManager.LIMITS:
            item = Gtk.CheckMenuItem(str(limit))
            item.set_draw_as_radio(True)
            item.set_active(options.limit == limit)

            def _set_limit(widget, limit=limit):
                self.set_limit(limit)

            item.connect("activate", _set_limit)
            limit_menu.append(item)

        position_item = Gtk.MenuItem(_("Position"))
        position_item.set_submenu(position_menu)
        menu.append(position_item)

        size_item = Gtk.MenuItem(_("Size"))
        size_item.set_submenu(size_menu)
        menu.append(size_item)

        limit_item = Gtk.MenuItem(_("Maximum Shown Images"))
        limit_item.set_submenu(limit_menu)
        menu.append(limit_item)

        menu.append(Gtk.SeparatorMenuItem.new())

        open_file = Gtk.MenuItem(os.path.basename(file).replace("_", "__"))

        def _open_file(widget):
            self.parent.open_file(widget, file)

        open_file.connect("activate", _open_file)
        menu.append(open_file)

        open_folder = Gtk.MenuItem(_("Show Containing Folder"))

        def _open_folder(widget):
            self.parent.open_folder(widget, file)

        open_folder.connect("activate", _open_folder)
        menu.append(open_folder)

        info = Util.read_metadata(file)
        if info and "sourceURL" in info and "sourceName" in info:
            url = info["sourceURL"]
            source_name = info["sourceName"]
            if "Fetched" in source_name:
                label = _("Fetched: Show Origin")
            else:
                label = _("View at %s") % source_name

            if len(label) > 50:
                label = label[:50] + "..."

            show_origin = Gtk.MenuItem(label)

            def _show_origin(widget=None):
                logger.info(lambda: "Opening url: " + url)
                webbrowser.open_new_tab(url)

            show_origin.connect("activate", _show_origin)
            menu.append(show_origin)

        menu.append(Gtk.SeparatorMenuItem.new())
        rating_item = Gtk.MenuItem(_("Set EXIF Rating"))
        rating_item.set_submenu(ThumbsManager.create_rating_menu(file, self.parent))
        if not os.access(file, os.W_OK):
            rating_item.set_sensitive(False)
        menu.append(rating_item)

        menu.append(Gtk.SeparatorMenuItem.new())

        self.copy_to_favorites = Gtk.MenuItem(_("Copy to _Favorites"))
        self.copy_to_favorites.set_use_underline(True)

        def _copy_to_favorites(widget):
            self.parent.copy_to_favorites(widget, file)

        self.copy_to_favorites.connect("activate", _copy_to_favorites)
        menu.append(self.copy_to_favorites)

        self.move_to_favorites = Gtk.MenuItem(_("Move to _Favorites"))
        self.move_to_favorites.set_use_underline(True)

        def _move_to_favorites(widget):
            self.parent.move_to_favorites(widget, file)
            self.remove_image(file)

        self.move_to_favorites.connect("activate", _move_to_favorites)
        self.move_to_favorites.set_visible(False)
        menu.append(self.move_to_favorites)

        trash_item = Gtk.MenuItem(_("Delete to _Trash"))
        trash_item.set_use_underline(True)

        def _trash(widget):
            self.parent.move_to_trash(widget, file)

        trash_item.connect("activate", _trash)
        menu.append(trash_item)

        focus = Gtk.MenuItem(_("Where is it from?"))
        focus.set_sensitive(self.parent.get_source(file) is not None)

        def _focus(widget):
            self.parent.focus_in_preferences(widget, file)

        focus.connect("activate", _focus)
        menu.append(focus)

        menu.append(Gtk.SeparatorMenuItem.new())

        def close(widget):
            self.hide(force=True)

        close_item = Gtk.MenuItem(_("Close"))
        close_item.connect("activate", close)
        menu.append(close_item)

        menu.show_all()

        favs_op = self.parent.determine_favorites_operation(file)
        self.parent.update_favorites_menuitems(self, False, favs_op)

        return menu

    @staticmethod
    def create_rating_menu(file, main_window):
        def _set_rating_maker(rating):
            def _set_rating(widget, rating=rating):
                try:
                    Util.set_rating(file, rating)
                    main_window.on_rating_changed(file)
                except Exception:
                    logger.exception(lambda: "Could not set EXIF rating")
                    main_window.show_notification(_("Could not set EXIF rating"))

            return _set_rating

        try:
            actual_rating = Util.get_rating(file)
        except Exception:
            actual_rating = None

        rating_menu = Gtk.Menu()
        for rating in range(5, 0, -1):
            item = Gtk.CheckMenuItem("\u2605" * rating)
            item.set_draw_as_radio(True)
            item.set_active(actual_rating == rating)
            item.set_sensitive(not item.get_active())
            item.connect("activate", _set_rating_maker(rating))
            rating_menu.append(item)

        rating_menu.append(Gtk.SeparatorMenuItem.new())

        unrated_item = Gtk.CheckMenuItem(_("Unrated"))
        unrated_item.set_draw_as_radio(True)
        unrated_item.set_active(actual_rating is None or actual_rating == 0)
        unrated_item.set_sensitive(not unrated_item.get_active())
        unrated_item.connect("activate", _set_rating_maker(None))
        rating_menu.append(unrated_item)

        rejected_item = Gtk.CheckMenuItem(_("Rejected"))
        rejected_item.set_draw_as_radio(True)
        rejected_item.set_active(actual_rating is not None and actual_rating < 0)
        rejected_item.set_sensitive(not rejected_item.get_active())
        rejected_item.connect("activate", _set_rating_maker(-1))
        rating_menu.append(rejected_item)

        rating_menu.show_all()
        return rating_menu

    def repaint(self):
        self.hide(keep_settings=True)
        if self.images:
            self.show(
                self.unlimited_images, screen=self.screen, type=self.type, folders=self.folders
            )

    def set_position(self, position):
        logger.info(lambda: "Setting thumbs position " + str(position))
        options = self.load_options()
        options.position = ThumbsManager.POSITIONS[position]
        self.save_options(options)
        self.repaint()

    def set_size(self, size):
        logger.info(lambda: "Setting thumbs size " + str(size))
        options = self.load_options()
        options.breadth = size
        self.save_options(options)
        self.repaint()

    def set_limit(self, limit):
        logger.info(lambda: "Setting thumbs limit " + str(limit))
        options = self.load_options()
        options.limit = limit
        self.save_options(options)
        self.repaint()

    def pin(self, widget=None):
        self.pinned = True

    def on_click(self, thumbs_window, file, widget, event):
        file = file
        self.pin()

        def _resume_scrolling(menu=None):
            thumbs_window.resume_scrolling()

        thumbs_window.pause_scrolling()
        if event.button == 1:
            if self.is_showing("history"):
                index = [info["eventbox"] for info in thumbs_window.all].index(widget)
                self.parent.move_to_history_position(index)
            else:
                self.parent.set_wallpaper(file)
            _resume_scrolling()
        else:
            menu = self.create_menu(file)

            def _compute_position(*args, **kwargs):
                x, y = event.get_root_coords()[0], event.get_root_coords()[1]
                h = menu.get_preferred_height()[1]
                return x, y - h if y - h >= 40 else y, True

            menu.connect("deactivate", _resume_scrolling)
            menu.popup(None, None, _compute_position, None, 0, event.time)

    def mark_active(self, file=None, position=None):
        self.active_file = file
        self.active_position = position
        if self.thumbs_window:
            if self.is_showing("history"):
                self.thumbs_window.mark_active(position=position)
            else:
                self.thumbs_window.mark_active(file=file)

    def show(self, images, screen=None, type=None, folders=None):
        options = self.load_options()
        with self.show_thumbs_lock:
            self.unlimited_images = images
            self.type = type
            limit = len(self.unlimited_images) if options.limit == self.UNLIMITED else options.limit
            self.images = self.unlimited_images[:limit]
            self.screen = screen
            self.folders = folders

            def _go():
                try:
                    if self.thumbs_window:
                        self.thumbs_window.destroy()
                        self.thumbs_window = None

                    if len(self.images) > 0:
                        self.initialize_thumbs_window()
                except Exception:
                    logger.exception(lambda: "Could not create thumbs window:")

            Util.add_mainloop_task(_go)

    def initialize_thumbs_window(self):
        options = self.load_options()

        def _go():
            self.thumbs_window = ThumbsWindow(
                screen=self.screen, position=options.position, breadth=options.breadth
            )
            try:
                icon = varietyconfig.get_data_file("media", "variety.svg")
                self.thumbs_window.set_icon_from_file(icon)
            except Exception:
                logger.exception(lambda: "Could not set thumbs window icon")

            if self.type == "history":
                title = _("Variety History")
            elif self.type == "downloads":
                title = _("Variety Recent Downloads")
            else:
                title = _("Variety Images")

            self.thumbs_window.set_title(title)
            self.thumbs_window.connect("clicked", self.on_click)

            def _on_close(window, event):
                self.hide(force=True)

            self.thumbs_window.connect("delete-event", _on_close)

            self.mark_active(self.active_file, self.active_position)

            self.thumbs_window.start(self.images)

        Util.add_mainloop_task(_go)

    def load_options(self):
        options = ThumbsManager.Options()
        try:
            config = ConfigObj(os.path.join(self.parent.config_folder, "ui.conf"))
            try:
                s = config["thumbs_position"].lower()
                options.position = ThumbsManager.POSITIONS[s]
            except Exception:
                logger.exception(lambda: "Missing or bad thumbs_position option in ui.conf")

            try:
                options.breadth = int(config["thumbs_size"])
            except Exception:
                logger.exception(lambda: "Missing or bad thumbs_size option in ui.conf")

            try:
                options.limit = (
                    int(config["thumbs_limit"])
                    if config["thumbs_limit"] != self.UNLIMITED
                    else self.UNLIMITED
                )
            except Exception:
                logger.exception(lambda: "Missing or bad thumbs_limit option in ui.conf")
        except Exception:
            logger.exception(lambda: "Could not read ui.conf")

        self.save_options(options)
        return options

    def save_options(self, options):
        try:
            config = ConfigObj(os.path.join(self.parent.config_folder, "ui.conf"))
            try:
                config["thumbs_position"] = ThumbsManager.R_POSITIONS[options.position]
                config["thumbs_size"] = options.breadth
                config["thumbs_limit"] = str(options.limit)
                config.write()
            except Exception:
                logger.exception(lambda: "Missing or bad thumbs_position option in ui.conf")
        except Exception:
            logger.exception(lambda: "Could not save ui.conf")

    def hide(self, force=True, keep_settings=False):
        if force:
            self.pinned = False

        if self.pinned:
            return

        if not keep_settings:
            self.type = None
            self.images = []
            self.screen = None
            self.folders = None

        if self.thumbs_window:

            def _go():
                self.thumbs_window.destroy()
                self.thumbs_window = None

            Util.add_mainloop_task(_go)
            self.parent.update_indicator(auto_changed=False)

    def remove_image(self, file):
        self.images = [f for f in self.images if f != file]
        if self.thumbs_window:
            if self.thumbs_window.fits_in_screen(+1000):
                self.repaint()
            else:
                self.thumbs_window.remove_image(file)

    def add_image(self, file):
        self.images.insert(0, file)
        if not self.thumbs_window:
            self.initialize_thumbs_window()
        else:
            self.thumbs_window.add_image(file, at_front=True)

    def is_showing(self, type):
        return self.type == type

    def get_folders(self):
        return self.folders
