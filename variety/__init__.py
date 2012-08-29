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

import optparse

import gettext
from gettext import gettext as _

DBUS_KEY = 'com.peterlevi.Variety'

DBUS_PATH = '/com/peterlevi/Variety'

gettext.textdomain('variety')

from gi.repository import Gtk, Gdk, GObject # pylint: disable=E0611

from variety import VarietyWindow
from variety.Util import Util

from variety_lib import set_up_logging, get_version

import os
import sys
import signal
import threading

import dbus, dbus.service, dbus.glib

class VarietyService(dbus.service.Object):
    def __init__(self, variety_window):
        self.variety_window = variety_window
        bus_name = dbus.service.BusName(DBUS_KEY, bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, DBUS_PATH)

    @dbus.service.method(dbus_interface=DBUS_KEY)
    def process_urls(self, urls):
        self.variety_window.process_urls(urls)

def parse_options():
    """Support for command line options"""
    parser = optparse.OptionParser(version="%%prog %s" % get_version())
    parser.add_option(
        "-v", "--verbose", action="count", dest="verbose",
        help=_("Show logging messages (-vv shows even finer debugging messages, -vvv debugs variety_lib too)"))
    (options, args) = parser.parse_args()

    set_up_logging(options)

    return args

VARIETY_WINDOW = None

def sigint_handler(a, b):
    print "CTRL-C pressed, quitting..."
    global VARIETY_WINDOW
    if VARIETY_WINDOW:
        VARIETY_WINDOW.on_quit()
    Util.start_force_exit_thread(10)

def main():
    args = parse_options()

    # ensure singleton
    if dbus.SessionBus().request_name(DBUS_KEY) != dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER:
        print "Variety is already running."
        if args:
            method = dbus.SessionBus().get_object(DBUS_KEY, DBUS_PATH).get_dbus_method("process_urls")
            method(args)
        return

    # ignore Ctrl-C
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the application.
    window = VarietyWindow.VarietyWindow()
    service = VarietyService(window)
    global VARIETY_WINDOW
    VARIETY_WINDOW = window
    window.first_run()

    if args:
        window.process_urls(args)

    GObject.threads_init()
    Gdk.threads_init()
    Gdk.threads_enter()
    Gtk.main()
    Gdk.threads_leave()
