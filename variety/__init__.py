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

import gettext
from gettext import gettext as _
import os
import sys
import signal
import dbus, dbus.service, dbus.glib
import logging

from gi.repository import Gtk, Gdk, GObject # pylint: disable=E0611

from variety import VarietyWindow
from variety import ThumbsManager
from variety import ThumbsWindow
from variety.Util import Util
from variety_lib import set_up_logging

DBUS_KEY = 'com.peterlevi.Variety'
DBUS_PATH = '/com/peterlevi/Variety'

gettext.textdomain('variety')

class VarietyService(dbus.service.Object):
    def __init__(self, variety_window):
        self.variety_window = variety_window
        bus_name = dbus.service.BusName(DBUS_KEY, bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, DBUS_PATH)

    @dbus.service.method(dbus_interface=DBUS_KEY, in_signature='as', out_signature='s')
    def process_command(self, arguments):
        result = self.variety_window.process_command(arguments, initial_run=False)
        return "" if result is None else result

VARIETY_WINDOW = None

terminate = False

def sigint_handler(*args):
    global terminate
    terminate = True

def check_quit():
    global terminate
    if not terminate:
        GObject.timeout_add(1000, check_quit)
        return

    logging.getLogger("variety").info("Terminating signal received, quitting...")
    print _("Terminating signal received, quitting...")

    global VARIETY_WINDOW
    if VARIETY_WINDOW:
        GObject.idle_add(VARIETY_WINDOW.on_quit)
    Util.start_force_exit_thread(10)

def main():
    # Ctrl-C
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigint_handler)
    signal.signal(signal.SIGQUIT, sigint_handler)

    Util.makedirs(os.path.expanduser("~/.config/variety/"))

    arguments = sys.argv[1:]
    # validate arguments and set up logging
    options, args = VarietyWindow.VarietyWindow.parse_options(arguments)
    set_up_logging(options)

    if options.verbose > 2:
        Util.log_all(VarietyWindow.VarietyWindow)
    if options.verbose > 3:
        Util.log_all(ThumbsManager.ThumbsManager)
        Util.log_all(ThumbsWindow.ThumbsWindow)

    bus = dbus.SessionBus()
    # ensure singleton
    if bus.request_name(DBUS_KEY) != dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER:
        if not arguments:
            arguments = ["--preferences"]
        print _("Variety is already running. Sending the command to the running instance.")
        method = bus.get_object(DBUS_KEY, DBUS_PATH).get_dbus_method("process_command")
        result = method(arguments)
        if result:
            print result
        return

    # Run the application.
    window = VarietyWindow.VarietyWindow()
    global VARIETY_WINDOW
    VARIETY_WINDOW = window
    service = VarietyService(window)

    bus.call_on_disconnection(window.on_quit)

    window.start(arguments)

    GObject.timeout_add(2000, check_quit)
    GObject.threads_init()
    Gdk.threads_init()
    Gdk.threads_enter()

    Gtk.main()
    Gdk.threads_leave()
