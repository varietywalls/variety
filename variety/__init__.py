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
import logging

gettext.textdomain('variety')
import os
import sys


def _u(s):
    if s is None:
        return s
    if isinstance(s, unicode):
        return s
    else:
        return unicode(s, 'utf8')


def _str(s):
    if s is None:
        return s
    if isinstance(s, unicode):
        return s.encode('utf8')
    else:
        return str(s)


def _(text):
    # Use "from locale import gettext" if we are deploying to /opt/extras
    # Use "from gettext import gettext" when using standard Debian deployment
    from gettext import gettext as _
    return _u(_(text))


def safe_print(text, ascii_text=None):
    """
    Python's print throws UnicodeEncodeError if the terminal encoding is borked. This version tries print, then logging, then printing the ascii text when one is present.
    If does not throw exceptions even if it fails.
    :param text: Text to print, str or unicode, possibly with non-ascii symbols in it
    :param ascii_text: optional. Original untranslated ascii version of the text when present.
    """
    try:
        print(text)
    except: # UnicodeEncodeError can happen here if the terminal is strangely configured, but we are playing safe and catching everything
        try:
            logging.getLogger("variety").error('Error printing non-ascii text, terminal encoding is %s' % sys.stdout.encoding)
            if ascii_text:
                try:
                    print ascii_text
                    return
                except:
                    pass
            logging.getLogger("variety").warning(text)
        except:
            pass


class SafeLogger(logging.Logger):
    """
    Fixes UnicodeDecodeErrors errors in logging calls:
    Accepts lambda instead of string messages. Catches errors when evaluatiating the passed lambda.
    """
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None):
        try:
            new_msg = msg if isinstance(msg, basestring) else msg()
        except:
            locale_info = 'Unknown'
            try:
                import os
                locale_info = 'Terminal encoding=%s, LANG=%s, LANGUAGE=%s' % (
                    sys.stdout.encoding, os.getenv('LANG'), os.getenv('LANGUAGE'))
                logging.getLogger("variety").exception('Errors while logging. Locale info: %s' % locale_info)
                # TODO gather and log more info here
            except:
                pass
            new_msg = 'Errors while logging. Locale info: %s' % locale_info

        return super(SafeLogger, self).makeRecord(name, level, fn, lno, new_msg, args, exc_info, func, extra)

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

from gi.repository import Gtk, Gdk, GObject # pylint: disable=E0611

from variety import VarietyWindow
from variety import ThumbsManager
from variety import ThumbsWindow
from variety.Util import Util
from variety_lib.helpers import set_up_logging

DBUS_KEY = 'com.peterlevi.Variety'
DBUS_PATH = '/com/peterlevi/Variety'


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
    safe_print(_("Terminating signal received, quitting..."),
               "Terminating signal received, quitting...")

    global VARIETY_WINDOW
    if VARIETY_WINDOW:
        GObject.idle_add(VARIETY_WINDOW.on_quit)
    Util.start_force_exit_thread(10)


def monkeypatch_ssl():
    """
    HTTPS connections may fail on Ubuntu 12.04 to servers with disabled SSL with this error:
    URLError: <urlopen error [Errno 1] _ssl.c:504: error:14077410:SSL routines:SSL23_GET_SERVER_HELLO:sslv3 alert handshake failure>.
    This monkeypatching routine fixes the issue by forcing it to use TLSv1 instead of SSL.
    Solution copied from http://askubuntu.com/questions/116020/python-https-requests-urllib2-to-some-sites-fail-on-ubuntu-12-04-without-proxy
    """
    import functools
    import ssl

    old_init = ssl.SSLSocket.__init__

    @functools.wraps(old_init)
    def ubuntu_openssl_bug_965371(self, *args, **kwargs):
        kwargs['ssl_version'] = ssl.PROTOCOL_TLSv1
        old_init(self, *args, **kwargs)

    ssl.SSLSocket.__init__ = ubuntu_openssl_bug_965371


def main():
    # Ctrl-C
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigint_handler)
    signal.signal(signal.SIGQUIT, sigint_handler)

    Util.makedirs(os.path.expanduser(u"~/.config/variety/"))

    arguments = map(_u, sys.argv[1:])

    # validate arguments and set up logging
    options, args = VarietyWindow.VarietyWindow.parse_options(arguments)
    set_up_logging(options.verbose)
    monkeypatch_ssl()

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
        safe_print(_("Variety is already running. Sending the command to the running instance."),
                   "Variety is already running. Sending the command to the running instance.")
        method = bus.get_object(DBUS_KEY, DBUS_PATH).get_dbus_method("process_command")
        result = method(arguments)
        if result:
            safe_print(result)
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
