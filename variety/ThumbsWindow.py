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

class ThumbsWindow(Gtk.Window):
    def __init__(self, parent=None, height=120):
        logger.debug("Creating thumb window %s, %d" % (str(self), time.time()))
        super(ThumbsWindow, self).__init__()

        self.running = True
        self.handlers = {}

        self.parent = parent
        self.set_decorated(False)
        #self.set_keep_above(False)

        self.height = height

        self.box = Gtk.Box(Gtk.Orientation.HORIZONTAL, 0)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.add_with_viewport(self.box)
        self.scroll.set_min_content_height(self.height)

        self.mouse_in = False
        self.mouse_position = None
        self.autoscroll_event = threading.Event()

        def mouse_enter(widget, event, data=None):
            self.mouse_in = True
            self.autoscroll_event.set()

        def mouse_motion(widget, event, data=None):
            self.mouse_position = (event.x, event.y)

        def mouse_leave(widget, event, data=None):
            self.mouse_in = False
            self.mouse_position = None

        self.eventbox = Gtk.EventBox()
        self.eventbox.set_visible(True)
        self.eventbox.add(self.scroll)
        self.eventbox.set_events(Gdk.EventMask.ENTER_NOTIFY_MASK |
                                 Gdk.EventMask.LEAVE_NOTIFY_MASK |
                                 Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        self.eventbox.connect('enter-notify-event', mouse_enter)
        self.eventbox.connect('leave-notify-event', mouse_leave)
        self.eventbox.connect('motion-notify-event', mouse_motion)

        self.add(self.eventbox)

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

        thumbs_thread = threading.Thread(target=self._thumbs_thread)
        thumbs_thread.daemon = True
        thumbs_thread.start()

        autoscroll_thread = threading.Thread(target=self._autoscroll_thread)
        autoscroll_thread.daemon = True
        autoscroll_thread.start()

    def _thumbs_thread(self):
        logger.debug("Starting thumb thread %s, %d" % (str(self), time.time()))
        try:
            total_width = 0
            shown = False

            for i, file in enumerate(self.images):
                if not self.running:
                    Gdk.threads_enter()
                    self.destroy()
                    Gdk.threads_leave()
                    return

                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file, 10000, self.height)
                except Exception:
                    continue

                Gdk.threads_enter()

                if not shown:
                    self.set_default_size(10, 10)
                    logger.debug("Showing thumb window %s, %d" % (str(self), time.time()))
                    self.show_all()
                    self.move(self.screen_width // 2, self.screen_height - self.height - 0)
                    shown = True

                #logger.debug("Thumbing " + file)

                thumb = Gtk.Image()
                thumb.set_from_pixbuf(pixbuf)
                thumb.set_visible(True)

                eventbox = Gtk.EventBox()
                eventbox.set_visible(True)

                def click(widget, event, file=file):
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

                eventbox.connect("button-release-event", click)
                eventbox.add(thumb)

                total_width += pixbuf.get_width()
                self.box.pack_start(eventbox, False, False, 0)

                if total_width < self.screen_width + 1000:
                    self.move(max(0, (self.screen_width - total_width) // 2), self.screen_height - self.height)
                    self.scroll.set_min_content_width(min(total_width, self.screen_width))

                Gdk.threads_leave()

                # we must yield from time to time, or GTK/cairo errors abound
                time.sleep(0.02)

                self.image_count = i

        except Exception:
            Gdk.threads_leave()
            logger.exception("Error while creating thumbs:")

    def destroy(self, widget=False):
        logger.debug("Destroying thumb window %s, %d" % (str(self), time.time()))
        self.running = False
        super(ThumbsWindow, self).destroy()

    def connect(self, key, handler):
        self.handlers.setdefault(key, []).append(handler)

    def _autoscroll_thread(self):
        last_update = time.time()
        while self.running:
            while not self.mouse_in:
                self.autoscroll_event.wait()

            time.sleep(max(0, last_update + 0.005 - time.time()))

            if not self.mouse_position:
                continue

            x = self.mouse_position[0]
            y = self.mouse_position[1]

            Gdk.threads_enter()
            pos = self.scroll.get_hadjustment()
            if y > 0:
                total_width = self.scroll.get_min_content_width()

                left_limit = total_width / 4
                right_limit = 3 * total_width / 4

                if x <= left_limit and pos.get_value() > pos.get_lower():
                    speed = 20 * (left_limit - x)**3 / left_limit**3
                    pos.set_value(max(pos.get_lower(), pos.get_value() - speed))
                elif x >= right_limit and pos.get_value() < pos.get_upper():
                    speed = 20 * (x - right_limit)**3 / (total_width - right_limit)**3
                    pos.set_value(min(pos.get_upper(), pos.get_value() + speed))
            Gdk.threads_leave()

            last_update = time.time()

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
    win.start(images)

    GObject.threads_init()
    Gdk.threads_init()
    Gdk.threads_enter()
    print "gtk main"
    Gtk.main()
    Gdk.threads_leave()

