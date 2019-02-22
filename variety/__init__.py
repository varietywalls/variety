# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (c) 2012-2018, Peter Levi <peterlevi@peterlevi.com>
# Copyright (c) 2017-2018, James Lu <james@overdrivenetworks.com>
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
import logging

gettext.textdomain('variety')
import os
import sys

def _(text):
    """Returns the translated form of text."""
    return gettext.gettext(text)

def safe_print(text, ascii_text=None):
    """
    Python's print throws UnicodeEncodeError if the terminal encoding is borked. This version tries print, then logging, then printing the ascii text when one is present.
    If does not throw exceptions even if it fails.
    :param text: Text to print, str or unicode, possibly with non-ascii symbols in it
    :param ascii_text: optional. Original untranslated ascii version of the text when present.
    """
    try:
        print(text)
    except:  # UnicodeEncodeError can happen here if the terminal is strangely configured, but we are playing safe and catching everything
        try:
            logging.getLogger("variety").error(
                'Error printing non-ascii text, terminal encoding is %s' % sys.stdout.encoding)
            if ascii_text:
                try:
                    print(ascii_text)
                    return
                except:
                    pass
            logging.getLogger("variety").warning(text)
        except:
            pass


class SafeLogger(logging.Logger):
    """
    Fixes UnicodeDecodeErrors errors in logging calls:
    Accepts lambda as well string messages. Catches errors when evaluating the passed lambda.
    """

    def makeRecord(self, name, level, fn, lno, msg, *args, **kwargs):
        try:
            new_msg = msg if isinstance(msg, str) else msg()
        except:
            locale_info = 'Unknown'
            try:
                locale_info = 'Terminal encoding=%s, LANG=%s, LANGUAGE=%s' % (
                    sys.stdout.encoding, os.getenv('LANG'), os.getenv('LANGUAGE'))
                logging.getLogger("variety").exception('Errors while logging. Locale info: %s' % locale_info)
                # TODO gather and log more info here
            except:
                pass
            new_msg = 'Errors while logging. Locale info: %s' % locale_info

        return super().makeRecord(name, level, fn, lno, new_msg, *args, **kwargs)


logging.setLoggerClass(SafeLogger)

# # Change default encoding from ascii to UTF8 - works OK on Linux and prevents various UnicodeEncodeErrors/UnicodeDecodeErrors
# Still, generally considerd bad practice, may cause some deep hidden errors, as various Python stuff depends on it
# reload(sys)
# sys.setdefaultencoding('UTF8')

import signal
import dbus, dbus.service, dbus.glib
import logging

import gi

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gdk, GObject  # pylint: disable=E0611

from variety import VarietyWindow
from variety import ThumbsManager
from variety import ThumbsWindow
from variety.Util import Util, ModuleProfiler
from variety_lib.helpers import set_up_logging

DBUS_KEY = 'com.peterlevi.Variety'
DBUS_PATH = '/com/peterlevi/Variety'


class VarietyService(dbus.service.Object):
    def __init__(self, variety_window):
        self.variety_window = variety_window
        bus_name = dbus.service.BusName(DBUS_KEY, bus=dbus.SessionBus())
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
    safe_print(_("Terminating signal received, quitting..."),
               "Terminating signal received, quitting...")

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

    bus = dbus.SessionBus()
    # ensure singleton
    if bus.request_name(DBUS_KEY) != dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER:
        if not arguments:
            arguments = ["--preferences"]
        safe_print(_("Variety is already running. Sending the command to the running instance."),
                   "Variety is already running. Sending the command to the running instance.")
        method = bus.get_object(DBUS_KEY, DBUS_PATH).get_dbus_method("process_command")
        result = method(arguments)
        if result:
            safe_print(result)
        return

    # validate arguments and set up logging
    # set_up_logging must be called after the DBus checks, only by one running instance,
    # or the log file can be corrupted
    options, args = VarietyWindow.VarietyWindow.parse_options(arguments)
    set_up_logging(options.verbose)

    if options.verbose >= 3:
        profiler = ModuleProfiler()
        if options.verbose >= 5:
            # The main variety package
            pkgname = os.path.dirname(__file__)
            profiler.log_path(pkgname)

            if options.verbose >= 6:
                # Track variety_lib
                profiler.log_path(pkgname + "_lib")
        else:
            # Cherry-picked log items carried over from variety 0.6.x
            profiler.log_class(VarietyWindow.VarietyWindow)

            if options.verbose >= 4:
                profiler.log_class(ThumbsManager.ThumbsManager)
                profiler.log_class(ThumbsWindow.ThumbsWindow)

        profiler.start()

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
