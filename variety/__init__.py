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

import dbus, dbus.service, dbus.glib
import logging
import os
import signal
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject  # pylint: disable=E0611


class SafeLogger(logging.Logger):
    """
    Fixes UnicodeDecodeErrors errors in logging calls:
    Accepts lambda as well string messages. Catches errors when evaluating the passed lambda.
    """

    def makeRecord(self, name, level, fn, lno, msg, *args, **kwargs):
        try:
            new_msg = msg if isinstance(msg, str) else msg()
        except:
            locale_info = "Unknown"
            try:
                locale_info = "Terminal encoding=%s, LANG=%s, LANGUAGE=%s" % (
                    sys.stdout.encoding,
                    os.getenv("LANG"),
                    os.getenv("LANGUAGE"),
                )
                logging.getLogger("variety").exception(
                    "Errors while logging. Locale info: %s" % locale_info
                )
                # TODO gather and log more info here
            except:
                pass
            new_msg = "Errors while logging. Locale info: %s" % locale_info

        return super().makeRecord(name, level, fn, lno, new_msg, *args, **kwargs)


logging.setLoggerClass(SafeLogger)


# these must be after the setLoggerClass call, as they obtain the variety logger
from variety import VarietyWindow, ThumbsManager, ThumbsWindow
from variety.profile import set_profile_path, get_profile_path, is_default_profile, get_profile_id
from variety.Util import Util, _, ModuleProfiler, safe_print


# # Change default encoding from ascii to UTF8 - works OK on Linux and prevents various UnicodeEncodeErrors/UnicodeDecodeErrors
# Still, generally considerd bad practice, may cause some deep hidden errors, as various Python stuff depends on it
# reload(sys)
# sys.setdefaultencoding('UTF8')


def _get_dbus_key():
    """
    DBus key for Variety.
    Variety uses a different key per profile, so several instances can run simultaneously if
    running with different profiles.
    Command any instance from the terminal by passing explicitly the same --profile options as it
    was started with.
    :return: the dbus key
    """
    if is_default_profile():
        return "com.peterlevi.Variety"
    else:
        return "com.peterlevi.Variety_{}".format(get_profile_id())


DBUS_PATH = "/com/peterlevi/Variety"


class VarietyService(dbus.service.Object):
    def __init__(self, variety_window):
        self.variety_window = variety_window
        bus_name = dbus.service.BusName(_get_dbus_key(), bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, DBUS_PATH)

    @dbus.service.method(dbus_interface=_get_dbus_key(), in_signature="as", out_signature="s")
    def process_command(self, arguments):
        result = self.variety_window.process_command(arguments, initial_run=False)
        return "" if result is None else result


VARIETY_WINDOW = None

terminate = False


def _sigint_handler(*args):
    global terminate
    terminate = True


def _check_quit():
    global terminate
    if not terminate:
        GObject.timeout_add(1000, _check_quit)
        return

    logging.getLogger("variety").info("Terminating signal received, quitting...")
    safe_print(
        _("Terminating signal received, quitting..."),
        "Terminating signal received, quitting...",
        file=sys.stderr,
    )

    global VARIETY_WINDOW
    if VARIETY_WINDOW:
        VARIETY_WINDOW.on_quit()
    Util.start_force_exit_thread(10)


def _set_up_logging(verbose):
    # add a handler to prevent basicConfig
    root = logging.getLogger()
    null_handler = logging.NullHandler()
    root.addHandler(null_handler)

    formatter = logging.Formatter("%(levelname)s: %(asctime)s: %(funcName)s() '%(message)s'")

    logger = logging.getLogger("variety")
    logger_sh = logging.StreamHandler()
    logger_sh.setFormatter(formatter)
    logger.addHandler(logger_sh)

    try:
        logger_file = logging.FileHandler(os.path.join(get_profile_path(), "variety.log"), "w")
        logger_file.setFormatter(formatter)
        logger.addHandler(logger_file)
    except Exception:
        logger.exception("Could not create file logger")

    lib_logger = logging.getLogger("variety_lib")
    lib_logger_sh = logging.StreamHandler()
    lib_logger_sh.setFormatter(formatter)
    lib_logger.addHandler(lib_logger_sh)

    logger.setLevel(logging.INFO)
    # Set the logging level to show debug messages.
    if verbose >= 2:
        logger.setLevel(logging.DEBUG)
    elif not verbose:
        # If we're not in verbose mode, only log these messages to file. This prevents
        # flooding syslog and/or ~/.xsession-errors depending on how variety was started:
        # (https://bugs.launchpad.net/variety/+bug/1685003)
        # XXX: We should /really/ make the internal debug logging use logging.debug,
        # this is really just a bandaid patch.
        logger_sh.setLevel(logging.WARNING)

    if verbose >= 3:
        lib_logger.setLevel(logging.DEBUG)


def main():
    if os.geteuid() == 0:
        print(
            'Variety is not supposed to run as root.\n'
            'You should NEVER run desktop apps as root, unless they are supposed to make '
            'system-global changes and you know very well what you are doing.\n'
            'Please run it with your normal user.\n'
            '\n'
            'If you are trying to run as root because Variety does not start at all with your normal '
            'user, you may be hitting a file permission issue or a bug.\n'
            'Here is what to do to troubleshoot:\n'
            '\n'
            '1. Open a terminal and run "variety -v" with your normal user.\n'
            'Look for exceptions and hints in the log for what the problem might be.\n'
            '\n'
            '2. You may try to rename ~/.config/variety to ~/.config/variety_bak and try again.\n'
            'This will have Variety start from a clean state.\n'
            'Your old config and images will remain in variety_bak\n'
            '\n'
            '3. If none of these help, open a bug in https://github.com/varietywalls/variety/issues '
            'and follow the instructions there.'
        )
        sys.exit(1)

    # Ctrl-C
    signal.signal(signal.SIGINT, _sigint_handler)
    signal.signal(signal.SIGTERM, _sigint_handler)
    signal.signal(signal.SIGQUIT, _sigint_handler)

    arguments = sys.argv[1:]

    # validate arguments
    from variety import VarietyOptionParser

    options, args = VarietyOptionParser.parse_options(arguments)
    set_profile_path(options.profile)
    Util.makedirs(get_profile_path())

    # ensure singleton per profile
    bus = dbus.SessionBus()
    dbus_key = _get_dbus_key()
    if bus.request_name(dbus_key) != dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER:
        if not arguments or (options.profile and len(arguments) <= 2):
            arguments = ["--preferences"]
        safe_print(
            _("Variety is already running. Sending the command to the running instance."),
            "Variety is already running. Sending the command to the running instance.",
            file=sys.stderr,
        )
        method = bus.get_object(dbus_key, DBUS_PATH).get_dbus_method("process_command")
        result = method(arguments)
        if result:
            safe_print(result)
        return

    # set up logging
    # set_up_logging must be called after the DBus checks, only by one running instance,
    # or the log file can be corrupted
    _set_up_logging(options.verbose)
    logging.getLogger("variety").info(lambda: "Using profile folder {}".format(get_profile_path()))

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
    GObject.timeout_add(2000, _check_quit)
    Gtk.main()
