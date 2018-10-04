#!/usr/bin/env python

import os
import gi
import cairo

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gdk, GObject

from variety import VARIETY_WINDOW

class FloatingWindow(Gtk.Window):
    __gtype_name__ = "FloatingWindow"

    def __init__(self):
        super().__init__()

        self.running = True

        #self.set_decorated(False)
        self.set_accept_focus(True)
        self.set_resizable(False)
        self.set_default_size(48, 48)

        self.connect('draw', self.draw)

        # Try rgba mode if compositing is on
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            self.set_opacity(0.8)

        self.set_app_paintable(True)

        self._eventbox = Gtk.EventBox()
        self._eventbox.set_visible(True)
        # Handle button press & left mouse button
        self._eventbox.set_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON1_MOTION_MASK)
        self._eventbox.connect('motion-notify-event', self.handle_drag)
        self._eventbox.connect('button-press-event', self.handle_click)

        self._image = Gtk.Image.new_from_icon_name("variety", Gtk.IconSize.DIALOG)
        self._eventbox.add(self._image)

        self.add(self._eventbox)
        self.show_all()

        self._last_offset = None

    def draw(self, widget, context):
        """
        Draws the window with transparent window background.
        """
        # Based off https://gist.github.com/KurtJacobson/374c8cb83aee4851d39981b9c7e2c22c
        context.set_source_rgba(0, 0, 0, 0)
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.paint()
        context.set_operator(cairo.OPERATOR_OVER)

    def handle_click(self, widget, event, data=None):
        """
        Handles mouse click:

        1) Find the offset from the cursor to the widget to assist with dragging.
           We want to allow dragging in the way that the cursor is at the same position
           relative to the window when the window moves (instead of moving with the cursor
           always at the top left).
        2) Bring up the Variety Menu when clicked.
        """
        self._last_offset = (event.x, event.y)

        # Maybe not the best practice, but I wanted this program to run in a standalone form
        # too for testing...
        if VARIETY_WINDOW:
            # stub
        else:
            print('Not showing menu; we were started in a standalone fashion.')

    def handle_drag(self, widget, event, data=None):
        """
        Handles drag movement when the left mouse button is clicked.
        """
        if self._last_offset:
            current_x, current_y = self.get_position()
            offset_x, offset_y = self._last_offset
            x = current_x + event.x - offset_x
            y = current_y + event.y - offset_y
            self.move(x, y)

if __name__ == "__main__":
    w = FloatingWindow()
    w.show()
    Gtk.main()
