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
import threading
import os
import time
import logging

logger = logging.getLogger('variety')

THUMBS_THREAD_DELAY = 0

class ThumbsWindow(Gtk.Window):
    def __init__(self, parent=None, height=120):
        super(ThumbsWindow, self).__init__()

        self.handlers = {}

        self.parent = parent
        self.set_decorated(False)
        #self.set_keep_above(False)

        self.height = height

        self.box = Gtk.Box(Gtk.Orientation.HORIZONTAL, 0)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.add_with_viewport(self.box)
        self.scroll.set_min_content_height(self.height)

        self.add(self.scroll)

        self.screen = Gdk.Screen.get_default()
        if self.parent:
            self.screen = self.parent.get_screen()
        self.screen_width = self.screen.get_width()
        self.screen_height = self.screen.get_height()

        self.menu = Gtk.Menu()
        close_item = Gtk.MenuItem("Close")
        close_item.connect("activate", self.destroy)
        pin_item = Gtk.MenuItem("Pin")
        pin_item.connect("activate", self.pin)
        self.menu.append(close_item)
        self.menu.append(pin_item)
        self.menu.show_all()

        self.pinned = False
        self.image_count = 0

    def pin(self, widget=None):
        self.pinned = True

    def start(self, images):
        self.images = images

        self.thread = threading.Thread(target=self._thumbs_thread)
        self.thread.daemon = True
        self.thread.start()

    def _thumbs_thread(self):
        try:
            time.sleep(THUMBS_THREAD_DELAY)

            self.running = True

            total_width = 0
            shown = False

            for i, file in enumerate(self.images):
                if not self.running:
                    return

                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file, 10000, self.height)
                except Exception:
                    continue

                Gdk.threads_enter()

                if not shown:
                    self.set_default_size(10, 10)
                    self.show_all()
                    self.move(self.screen_width // 2, self.screen_height - self.height - 0)
                    shown = True

                logger.debug("Thumbing " + file)

                thumb = Gtk.Image()
                thumb.set_from_pixbuf(pixbuf)
                thumb.set_visible(True)

                eventbox = Gtk.EventBox()
                eventbox.set_visible(True)

                def click_maker(file):
                    def click(widget, event):
                        if event.button == 1:
                            for func in self.handlers["clicked"]:
                                func(file, widget, event)
                        else:
                            self.menu.popup(
                                None,
                                self.box,
                                lambda x, y: (event.get_root_coords()[0], event.get_root_coords()[1], True),
                                None,
                                event.button,
                                event.time)

                    return click

                eventbox.connect("button-release-event", click_maker(file))
                eventbox.add(thumb)

                total_width += pixbuf.get_width()
                self.box.pack_start(eventbox, False, False, 0)

                if total_width < self.screen_width + 1000:
                    self.move(max(0, (self.screen_width - total_width) // 2), self.screen_height - self.height)
                if i < 20 or i % 10 == 0:
                    self.scroll.set_min_content_width(min(total_width, self.screen_width))

                Gdk.threads_leave()

                # we must yield from time to time, or GTK/cairo errors abound
                time.sleep(0.02)

                self.image_count = i

        except Exception:
            Gdk.threads_leave()
            logger.exception("Error while creating thumbs:")

    def destroy(self, widget=False):
        self.running = False
        if self.image_count <= 50:
            super(ThumbsWindow, self).destroy()
        else:
            # wait some time for running thread to finish
            timer = threading.Timer(0.2, super(ThumbsWindow, self).destroy)
            timer.start()

    def connect(self, key, handler):
        self.handlers.setdefault(key, []).append(handler)

if __name__ == "__main__":
    images = []
    dir = "/usr/share/backgrounds"
    for f in os.listdir(dir):
        file = os.path.join(dir, f)
        if os.path.isfile(file) and file.endswith(".jpg"):
            images.append(file)

    print images

    win = ThumbsWindow()
    win.connect("delete-event", Gtk.main_quit)

    print "starting"
    THUMBS_THREAD_DELAY = 0.5
    win.start(images)

    GObject.threads_init()
    Gdk.threads_init()
    Gdk.threads_enter()
    print "gtk main"
    Gtk.main()
    Gdk.threads_leave()

