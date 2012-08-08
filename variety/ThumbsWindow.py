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
    __gsignals__ = {
        'clicked': (GObject.SIGNAL_RUN_FIRST, None, (str,Gtk.Widget,object))
    }

    LEFT = 1
    RIGHT = 2
    BOTTOM = 3
    TOP = 4

    def __init__(self, screen=None, position=BOTTOM, breadth=120):
        logger.debug("Creating thumb window %s, %d" % (str(self), time.time()))
        super(ThumbsWindow, self).__init__()

        self.running = True

        self.set_decorated(False)

        self.screen = screen if screen else Gdk.Screen.get_default()
        self.screen_width = self.screen.get_width()
        self.screen_height = self.screen.get_height()

        self.position = position
        self.breadth = int(breadth * (1 if self.is_horizontal() else float(self.screen_width) / self.screen_height))

        self.box = Gtk.HBox(False, 0) if self.is_horizontal() else Gtk.VBox(False, 0)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.add_with_viewport(self.box)
        if self.is_horizontal():
            self.scroll.set_min_content_height(self.breadth)
        else:
            self.scroll.set_min_content_width(self.breadth)

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

        eventbox = Gtk.EventBox()
        eventbox.set_visible(True)
        eventbox.add(self.scroll)
        eventbox.set_events(Gdk.EventMask.ENTER_NOTIFY_MASK |
                            Gdk.EventMask.LEAVE_NOTIFY_MASK |
                            Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        eventbox.connect('enter-notify-event', mouse_enter)
        eventbox.connect('leave-notify-event', mouse_leave)
        eventbox.connect('motion-notify-event', mouse_motion)

        self.add(eventbox)

        self.image_count = 0

    def is_horizontal(self):
        return self.position == ThumbsWindow.TOP or self.position == ThumbsWindow.BOTTOM

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
                    if self.is_horizontal():
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file, 10000, self.breadth)
                    else:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file, self.breadth, 10000)
                except Exception:
                    continue

                Gdk.threads_enter()

                if not shown:
                    self.set_default_size(10, 10)
                    logger.debug("Showing thumb window %s, %d" % (str(self), time.time()))
                    self.show_all()
                    if self.position == ThumbsWindow.BOTTOM:
                        self.move(self.screen_width // 2, self.screen_height - self.breadth)
                    elif self.position == ThumbsWindow.TOP:
                        self.move(self.screen_width // 2, 0)
                    elif self.position == ThumbsWindow.LEFT:
                        self.move(0, self.screen_height // 2)
                    elif self.position == ThumbsWindow.RIGHT:
                        self.move(self.screen_width - self.screen_height, self.screen_height // 2)
                    else:
                        raise Exception("Unsupported thumbs position: " + str(self.position))
                    shown = True

                thumb = Gtk.Image()
                thumb.set_from_pixbuf(pixbuf)
                thumb.set_visible(True)

                eventbox = Gtk.EventBox()
                eventbox.set_visible(True)

                def click(widget, event, file=file):
                    self.emit("clicked", file, widget, event)
                eventbox.connect("button-release-event", click)
                eventbox.add(thumb)

                total_width += (pixbuf.get_width() if self.is_horizontal() else pixbuf.get_height())
                self.box.pack_start(eventbox, False, False, 0)

                if total_width < (self.screen_width if self.is_horizontal() else self.screen_height) + 1000:
                    if self.position == ThumbsWindow.BOTTOM:
                        self.move(max(0, (self.screen_width - total_width) // 2), self.screen_height - self.breadth)
                        self.scroll.set_min_content_width(min(total_width, self.screen_width))
                    elif self.position == ThumbsWindow.TOP:
                        self.move(max(0, (self.screen_width - total_width) // 2), 0)
                        self.scroll.set_min_content_width(min(total_width, self.screen_width))
                    elif self.position == ThumbsWindow.LEFT:
                        self.move(0, max(0, (self.screen_height - total_width) // 2))
                        self.scroll.set_min_content_height(min(total_width, self.screen_height))
                    elif self.position == ThumbsWindow.RIGHT:
                        self.move(self.screen_width - self.breadth, max(0, (self.screen_height - total_width) // 2))
                        self.scroll.set_min_content_height(min(total_width, self.screen_height))

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

    def autoscroll_step(self, adj, total_size, current):
        if not adj:
            return
        left_limit = total_size / 4
        right_limit = 3 * total_size / 4
        if current <= left_limit and adj.get_value() > adj.get_lower():
            speed = 30 * (left_limit - current) ** 3 / left_limit ** 3
            adj.set_value(max(adj.get_lower(), adj.get_value() - speed))
        elif current >= right_limit and adj.get_value() < adj.get_upper():
            speed = 30 * (current - right_limit) ** 3 / (total_size - right_limit) ** 3
            adj.set_value(min(adj.get_upper(), adj.get_value() + speed))

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
            if self.is_horizontal() and y > 0:
                self.autoscroll_step(self.scroll.get_hadjustment(), self.scroll.get_min_content_width(), x)
            elif not self.is_horizontal() and x > 0:
                self.autoscroll_step(self.scroll.get_vadjustment(), self.scroll.get_min_content_height(), y)

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

