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

from gi.repository import Gtk, Gdk, GdkPixbuf, GObject
from configobj import ConfigObj
import os

import threading
import logging
from variety.ThumbsWindow import ThumbsWindow
from variety_lib import varietyconfig

logger = logging.getLogger('variety')

class ThumbsManager():
    POSITIONS = {
        "bottom": ThumbsWindow.BOTTOM,
        "top": ThumbsWindow.TOP,
        "left": ThumbsWindow.LEFT,
        "right": ThumbsWindow.RIGHT
    }

    R_POSITIONS = dict((v, k) for (k,v) in POSITIONS.items())

    SIZES = [x*30 for x in xrange(2, 11)]

    class Options():
        def __init__(self):
            self.position = ThumbsWindow.BOTTOM
            self.breadth = 120

    def __init__(self, parent):
        self.parent = parent
        self.thumbs_window = None
        self.show_thumbs_lock = threading.Lock()

        self.pinned = False
        self.images = []
        self.screen = None

        self.type = None

        self.active_file = None
        self.active_position = None

    def create_menu(self, file):
        menu = Gtk.Menu()

        def close(widget): self.hide(gdk_thread=True, force=True)
        close_item = Gtk.MenuItem("Close")
        close_item.connect("activate", close)
        menu.append(close_item)

        options = self.load_options()

        position_menu = Gtk.Menu()
        for p, v in ThumbsManager.POSITIONS.items():
            item = Gtk.CheckMenuItem(p[0].upper() + p[1:])
            item.set_draw_as_radio(True)
            item.set_active(options.position == v)
            def _set_position(widget, pos=p): self.set_position(pos)
            item.connect("activate", _set_position)
            position_menu.append(item)

        size_menu = Gtk.Menu()
        for size in ThumbsManager.SIZES:
            item = Gtk.CheckMenuItem(str(size))
            item.set_draw_as_radio(True)
            item.set_active(options.breadth == size)
            def _set_size(widget, size=size): self.set_size(size)
            item.connect("activate", _set_size)
            size_menu.append(item)

        position_item = Gtk.MenuItem("Position")
        position_item.set_submenu(position_menu)
        menu.append(position_item)

        size_item = Gtk.MenuItem("Size")
        size_item.set_submenu(size_menu)
        menu.append(size_item)

        menu.append(Gtk.SeparatorMenuItem())

        open_file = Gtk.MenuItem("Open in Image Viewer")
        def _open_file(widget): self.parent.open_file(widget, file)
        open_file.connect("activate", _open_file)
        menu.append(open_file)

        open_folder = Gtk.MenuItem("Show Containing Folder")
        def _open_folder(widget): self.parent.open_folder(widget, file)
        open_folder.connect("activate", _open_folder)
        menu.append(open_folder)

        trash_item = Gtk.MenuItem("Move to Trash")
        def _trash(widget): self.parent.move_to_trash(widget, file)
        trash_item.connect("activate", _trash)
        menu.append(trash_item)

        in_favs = self.parent.is_in_favorites(file)
        favorites_item = Gtk.MenuItem()
        favorites_item.set_label("Already in Favorites" if in_favs else "Copy to Favorites")
        favorites_item.set_sensitive(not in_favs)
        def _favorite(widget): self.parent.copy_to_favorites(widget, file)
        if not in_favs:
            favorites_item.connect("activate", _favorite)
        menu.append(favorites_item)

        menu.show_all()

        return menu

    def repaint(self):
        self.hide(gdk_thread=True)
        if self.images:
            self.show(self.images, gdk_thread=True, screen=self.screen, type=self.type)

    def set_position(self, position):
        logger.info("Setting thumbs position " + str(position))
        options = self.load_options()
        options.position = ThumbsManager.POSITIONS[position]
        self.save_options(options)
        self.repaint()

    def set_size(self, size):
        logger.info("Setting thumbs size " + str(size))
        options = self.load_options()
        options.breadth = size
        self.save_options(options)
        self.repaint()

    def pin(self, widget=None):
        self.pinned = True

    def on_click(self, thumbs_window, file, widget, event):
        self.pin()
        if event.button == 1:
            if self.is_showing("history"):
                index = [info["eventbox"] for info in thumbs_window.all].index(widget)
                self.parent.move_to_history_position(index)
            else:
                self.parent.set_wallpaper(file, False)
        else:
            menu = self.create_menu(file)
            def _compute_position(a, b, event=event):
                x, y = event.get_root_coords()[0], event.get_root_coords()[1]
                h = menu.get_preferred_height()[1]
                return x, y - h if y - h >= 40 else y, True
            menu.popup(None, None, _compute_position, None, event.button, event.time)

    def mark_active(self, file=None, position=None):
        self.active_file = file
        self.active_position = position
        if self.thumbs_window:
            if self.is_showing("history"):
                self.thumbs_window.mark_active(position=position)
            else:
                self.thumbs_window.mark_active(file=file)

    def show(self, images, gdk_thread=False, screen=None, type=None):
        with self.show_thumbs_lock:
            self.type = type
            self.images = images
            self.screen = screen

            try:
                if self.thumbs_window:
                    if not gdk_thread:
                        Gdk.threads_enter()
                    self.thumbs_window.destroy()
                    self.thumbs_window = None
                    if not gdk_thread:
                        Gdk.threads_leave()

                if len(images) > 0:
                    if not gdk_thread:
                        Gdk.threads_enter()
                    options = self.load_options()
                    self.thumbs_window = ThumbsWindow(
                        screen=screen, position=options.position, breadth=options.breadth)
                    try:
                        icon = varietyconfig.get_data_file("media", "variety.svg")
                        self.thumbs_window.set_icon_from_file(icon)
                    except Exception:
                        logger.exception("Could not set thumbs window icon")

                    title = "Variety %s" % ("History" if self.type == "history" else "Images")
                    self.thumbs_window.set_title(title)
                    self.thumbs_window.connect("clicked", self.on_click)
                    def _on_close(window, event):
                        self.thumbs_window = None
                        self.parent.update_indicator(is_gtk_thread=True)
                    self.thumbs_window.connect("delete-event", _on_close)

                    self.mark_active(self.active_file, self.active_position)

                    self.thumbs_window.start(images)
                    if not gdk_thread:
                        Gdk.threads_leave()
            except Exception:
                logger.exception("Could not create thumbs window:")

    def load_options(self):
        options = ThumbsManager.Options()
        options.position = ThumbsWindow.BOTTOM
        options.breadth = 120
        try:
            config = ConfigObj(os.path.join(self.parent.config_folder, "ui.conf"))
            try:
                s = config["thumbs_position"].lower()
                options.position = ThumbsManager.POSITIONS[s]
            except Exception:
                logger.exception("Missing or bad thumbs_position option in ui.conf")

            try:
                options.breadth = int(config["thumbs_size"])
            except Exception:
                logger.exception("Missing or bad thumbs_size option in ui.conf")
        except Exception:
            logger.exception("Could not read ui.conf")

        return options

    def save_options(self, options):
        try:
            config = ConfigObj(os.path.join(self.parent.config_folder, "ui.conf"))
            try:
                config["thumbs_position"] = ThumbsManager.R_POSITIONS[options.position]
                config["thumbs_size"] = options.breadth
                config.write()
            except Exception:
                logger.exception("Missing or bad thumbs_position option in ui.conf")
        except Exception:
            logger.exception("Could not save ui.conf")


    def hide(self, gdk_thread=False, force=True):
        if force: self.pinned = False
        if self.thumbs_window and not self.pinned:
            try:
                if not gdk_thread:
                    Gdk.threads_enter()
                self.thumbs_window.destroy()
                self.thumbs_window = None
                self.parent.update_indicator(is_gtk_thread=True)
                if not gdk_thread:
                    Gdk.threads_leave()
            except Exception:
                pass

    def remove_image(self, file, gdk_thread=True):
        self.images = [f for f in self.images if f != file]
        if self.thumbs_window:
            if self.thumbs_window.fits_in_screen(+1000):
                self.repaint()
            else:
                self.thumbs_window.remove_image(file, gdk_thread)

    def add_image(self, file, gdk_thread=True):
        self.images.insert(0, file)
        if self.thumbs_window:
            self.thumbs_window.add_image(file, gdk_thread, at_front=True)

    def is_showing(self, type):
        return self.thumbs_window is not None and self.type == type


