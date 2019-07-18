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
import time

from gi.repository import Gdk, GdkPixbuf, GObject, Gtk

from variety.profile import get_profile_wm_class
from variety.Util import Util, on_gtk

logger = logging.getLogger("variety")


class ThumbsWindow(Gtk.Window):
    __gsignals__ = {"clicked": (GObject.SIGNAL_RUN_FIRST, None, (str, Gtk.Widget, object))}

    LEFT = 1
    RIGHT = 2
    BOTTOM = 3
    TOP = 4

    def __init__(self, screen=None, position=BOTTOM, breadth=120):
        logger.debug(lambda: "Creating thumb window %s, %d" % (str(self), time.time()))
        super(ThumbsWindow, self).__init__()

        self.set_wmclass(get_profile_wm_class(), get_profile_wm_class())

        self.running = True

        self.set_decorated(False)
        self.set_accept_focus(False)

        self.screen = screen if screen else Gdk.Screen.get_default()
        self.screen_width = self.screen.get_width()
        self.screen_height = self.screen.get_height()

        self.position = position
        self.breadth = int(
            breadth * (1 if self.is_horizontal() else float(self.screen_width) / self.screen_height)
        )

        self.box = Gtk.HBox(False, 0) if self.is_horizontal() else Gtk.VBox(False, 0)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.add_with_viewport(self.box)
        if self.is_horizontal():
            self.scroll.set_min_content_height(self.breadth)
            self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        else:
            self.scroll.set_min_content_width(self.breadth)
            self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.mouse_in = False
        self.mouse_position = None
        self.autoscroll_event = threading.Event()
        self.scrolling_paused = False
        self.scrolling_locked = False

        def mouse_enter(widget, event, data=None):
            self.mouse_in = True
            self.previous_speed = 0
            self.autoscroll_event.set()

        def mouse_motion(widget, event, data=None):
            self.mouse_position = (event.x, event.y)
            if not self.scrolling_locked:
                self.scrolling_paused = False

        def mouse_leave(widget, event, data=None):
            self.mouse_in = False
            self.mouse_position = None
            self.previous_speed = 0
            self.autoscroll_event.clear()

        eventbox = Gtk.EventBox()
        eventbox.set_visible(True)
        eventbox.add(self.scroll)
        eventbox.set_events(
            Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )
        eventbox.connect("enter-notify-event", mouse_enter)
        eventbox.connect("leave-notify-event", mouse_leave)
        eventbox.connect("motion-notify-event", mouse_motion)

        self.add(eventbox)

        self.image_count = 0

        self.active_file = None
        self.active_position = None
        self.mark = None
        self.marked_info = None

        self.all = []

    def pause_scrolling(self):
        self.previous_speed = 0
        self.scrolling_paused = True
        self.scrolling_locked = True

    def resume_scrolling(self):
        self.scrolling_locked = False

    def is_horizontal(self):
        return self.position == ThumbsWindow.TOP or self.position == ThumbsWindow.BOTTOM

    def pin(self, widget=None):
        self.pinned = True

    @on_gtk
    def start(self, images):
        self.images = images

        self._show()

        thumbs_thread = threading.Thread(target=self._thumbs_thread)
        thumbs_thread.daemon = True
        thumbs_thread.start()

        autoscroll_thread = threading.Thread(target=self._autoscroll_thread)
        autoscroll_thread.daemon = True
        autoscroll_thread.start()

    def _show(self):
        self.set_default_size(1, 1)
        logger.debug(lambda: "Showing thumb window %s, %d" % (str(self), time.time()))
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
        self.show_all()

    def _thumbs_thread(self):
        logger.debug(lambda: "Starting thumb thread %s, %d" % (str(self), time.time()))
        try:
            self.total_width = 0

            for i, file in enumerate(self.images):
                if not self.running:
                    Util.add_mainloop_task(self.destroy)
                    return

                self.add_image(file, at_front=False)
                self.image_count = i

        except Exception:
            logger.exception(lambda: "Error while creating thumbs:")

    def add_image(self, file, at_front=False):
        try:
            if self.is_horizontal():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file, 10000, self.breadth)
            else:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file, self.breadth, 10000)
        except Exception:
            logger.warning(
                lambda: "Could not create thumbnail for file %s. File may be missing or invalid."
                % file
            )
            pixbuf = None

        def _go():
            image_size = (
                0
                if not pixbuf
                else pixbuf.get_width()
                if self.is_horizontal()
                else pixbuf.get_height()
            )

            thumb = Gtk.Image()
            if pixbuf:
                thumb.set_from_pixbuf(pixbuf)
            thumb.set_visible(True)

            overlay = Gtk.Overlay()
            overlay.add(thumb)
            overlay.set_visible(True)

            eventbox = Gtk.EventBox()
            eventbox.set_visible(True)

            def click(widget, event, file=file):
                self.emit("clicked", file, widget, event)

            eventbox.connect("button-release-event", click)
            eventbox.add(overlay)

            image_info = {
                "file": file,
                "eventbox": eventbox,
                "thumb": thumb,
                "size": image_size,
                "overlay": overlay,
            }
            if at_front:
                image_info["start"] = 0
                for info in self.all:
                    info["start"] += image_size
                self.all.insert(0, image_info)
                position = 0
            else:
                image_info["start"] = self.total_width
                self.all.append(image_info)
                position = len(self.all) - 1

            self.total_width += image_size

            adj = (
                self.scroll.get_hadjustment()
                if self.is_horizontal()
                else self.scroll.get_vadjustment()
            )
            scrollbar_at_start = not adj or adj.get_value() <= adj.get_lower() + 20

            self.box.pack_start(eventbox, False, False, 0)

            if at_front:
                self.box.reorder_child(eventbox, 0)
                # get adj again - we just added at front, scrollbar might have appeared
                adj = (
                    self.scroll.get_hadjustment()
                    if self.is_horizontal()
                    else self.scroll.get_vadjustment()
                )
                if adj:
                    if scrollbar_at_start:
                        adj.set_value(adj.get_lower())
                    else:
                        adj.set_value(adj.get_value() + image_size)

            self.update_size()

            if file == self.active_file or position == self.active_position:
                self.mark_active(self.active_file, self.active_position)

        Util.add_mainloop_task(_go)

    def update_size(self):
        if (
            self.total_width
            < (self.screen_width if self.is_horizontal() else self.screen_height) + 1000
        ):
            if self.position == ThumbsWindow.BOTTOM:
                self.move(
                    max(0, (self.screen_width - self.total_width) // 2),
                    self.screen_height - self.breadth,
                )
                self.scroll.set_min_content_width(min(self.total_width, self.screen_width))
            elif self.position == ThumbsWindow.TOP:
                self.move(max(0, (self.screen_width - self.total_width) // 2), 0)
                self.scroll.set_min_content_width(min(self.total_width, self.screen_width))
            elif self.position == ThumbsWindow.LEFT:
                self.move(0, max(0, (self.screen_height - self.total_width) // 2))
                self.scroll.set_min_content_height(min(self.total_width, self.screen_height))
            elif self.position == ThumbsWindow.RIGHT:
                self.move(
                    self.screen_width - self.breadth,
                    max(0, (self.screen_height - self.total_width) // 2),
                )
                self.scroll.set_min_content_height(min(self.total_width, self.screen_height))

    # TODO this method is buggy when width < screen and scrollbar not shown - a blank space remains
    @on_gtk
    def remove_image(self, image):
        for info in self.all:
            if info["file"] == image:
                eventbox = info["eventbox"]
                thumb = info["thumb"]
                self.box.remove(eventbox)
                eventbox.destroy()
                thumb.destroy()
                self.total_width -= info["size"]
                self.update_size()

        self.all = [info for info in self.all if info["file"] != image]

    def mark_active(self, file=None, position=None):
        def _mark():
            logger.debug(lambda: "Marking file %s, position %s" % (file, str(position)))

            self.active_file = file
            self.active_position = position

            pos = position
            if self.active_file:
                try:
                    pos = [info["file"] for info in self.all].index(self.active_file)
                except Exception:
                    pass

            if self.mark:
                if self.marked_info:
                    self.marked_info["overlay"].remove(self.mark)
                    self.marked_info = None
                self.mark.destroy()
                self.mark = None

            if pos is not None and len(self.all) > pos:
                self.marked_info = self.all[pos]

                image_size = self.marked_info["size"]

                self.mark = Gtk.DrawingArea()
                if self.is_horizontal():
                    self.mark.set_size_request(image_size, 5)
                    self.mark.set_valign(Gtk.Align.START)
                    self.mark.set_halign(Gtk.Align.CENTER)
                else:
                    self.mark.set_size_request(5, image_size)
                    self.mark.set_valign(Gtk.Align.CENTER)
                    self.mark.set_halign(Gtk.Align.START)

                def _draw_callback(widget, cr):
                    if self.is_horizontal():
                        cr.rectangle(0, 0, image_size, 5)
                    else:
                        cr.rectangle(0, 0, 5, image_size)
                    cr.set_source_rgba(255.0 / 255, 105.0 / 255, 44.0 / 255)
                    cr.fill()
                    return False

                self.mark.connect("draw", _draw_callback)
                self.mark.set_visible(True)

                self.marked_info["overlay"].add_overlay(self.mark)

        GObject.idle_add(_mark)

    def fits_in_screen(self, with_reserve=0):
        if self.is_horizontal():
            return self.total_width < self.screen_width + with_reserve

    def destroy(self, widget=False):
        logger.debug(lambda: "Destroying thumb window %s, %d" % (str(self), time.time()))
        self.running = False
        self.autoscroll_event.set()
        super(ThumbsWindow, self).destroy()

    def autoscroll_step(self, adj, total_size, current):
        if not adj:
            return

        if not hasattr(self, "previous_speed"):
            self.previous_speed = 0

        left_limit = total_size / 5
        right_limit = 4 * total_size / 5

        if current <= left_limit and adj.get_value() > adj.get_lower():
            speed = 30 * (left_limit - current) ** 3 / left_limit ** 3
            if adj.get_value() < adj.get_lower() + 800:
                speed = speed * (adj.get_value() - adj.get_lower()) / 800
            speed = min(speed, self.previous_speed + 0.1)
            self.previous_speed = speed
            adj.set_value(max(adj.get_lower(), adj.get_value() - speed))
        elif current >= right_limit and adj.get_value() < adj.get_upper():
            speed = 30 * (current - right_limit) ** 3 / (total_size - right_limit) ** 3
            if adj.get_value() > adj.get_upper() - adj.get_page_size() - 800:
                speed = speed * (adj.get_upper() - adj.get_page_size() - adj.get_value()) / 800
            speed = min(speed, self.previous_speed + 0.1)
            self.previous_speed = speed
            adj.set_value(min(adj.get_upper(), adj.get_value() + speed))

    def _autoscroll_thread(self):
        last_update = time.time()
        while self.running:
            while not self.mouse_in:
                if not self.running:
                    return
                self.autoscroll_event.wait(10)

            time.sleep(max(0, last_update + 0.005 - time.time()))

            if not self.mouse_position or self.scrolling_paused:
                continue

            x = self.mouse_position[0]
            y = self.mouse_position[1]

            def _go():
                if self.is_horizontal() and y > 0:
                    self.autoscroll_step(
                        self.scroll.get_hadjustment(), self.scroll.get_min_content_width(), x
                    )
                elif not self.is_horizontal() and x > 0:
                    self.autoscroll_step(
                        self.scroll.get_vadjustment(), self.scroll.get_min_content_height(), y
                    )

            Util.add_mainloop_task(_go)

            last_update = time.time()


if __name__ == "__main__":
    images = []
    dir = "/usr/share/backgrounds"
    for f in os.listdir(dir):
        file = os.path.join(dir, f)
        if os.path.isfile(file) and file.endswith(".jpg"):
            images.append(file)

    print(images)

    win = ThumbsWindow()
    win.connect("delete-event", Gtk.main_quit)

    print("starting")
    win.start(images)
    print("gtk main")
    Gtk.main()
