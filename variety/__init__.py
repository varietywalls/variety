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

import gettext
from gettext import gettext as _
import sys

DBUS_KEY = 'com.peterlevi.Variety'

DBUS_PATH = '/com/peterlevi/Variety'

gettext.textdomain('variety')

from gi.repository import Gtk, Gdk, GObject # pylint: disable=E0611

from variety import VarietyWindow
from variety.Util import Util

from variety_lib import set_up_logging, get_version

import signal

import dbus, dbus.service, dbus.glib

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

def sigint_handler(a, b):
    print _("CTRL-C pressed, quitting...")
    global VARIETY_WINDOW
    if VARIETY_WINDOW:
        VARIETY_WINDOW.on_quit()
    Util.start_force_exit_thread(10)

def main():
    arguments = sys.argv[1:]
    # validate arguments and set up logging
    options, args = VarietyWindow.VarietyWindow.parse_options(arguments)
    set_up_logging(options)

    # ensure singleton
    if dbus.SessionBus().request_name(DBUS_KEY) != dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER:
        if not arguments:
            arguments = ["--preferences"]
        print _("Variety is already running. Sending the command to the running instance.")
        method = dbus.SessionBus().get_object(DBUS_KEY, DBUS_PATH).get_dbus_method("process_command")
        result = method(arguments)
        if result:
            print result
        return

    # ignore Ctrl-C
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the application.
    window = VarietyWindow.VarietyWindow()
    global VARIETY_WINDOW
    VARIETY_WINDOW = window
    service = VarietyService(window)

    window.start(options)
    window.process_command(arguments, initial_run=True)

    GObject.threads_init()
    Gdk.threads_init()
    Gdk.threads_enter()
    Gtk.main()
    Gdk.threads_leave()
