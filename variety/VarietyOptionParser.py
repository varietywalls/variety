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

import optparse

from variety.Util import _, safe_print
from variety_lib import varietyconfig


class VarietyOptionParser(optparse.OptionParser):
    """Override optparse.OptionParser to allow for errors in options without exiting"""

    def __init__(self, usage, version, report_errors=True):
        optparse.OptionParser.__init__(self, usage=usage, version=version)
        self.report_errors = report_errors

    def print_help(self, file=None):
        """print_help(file : file = stdout)

        Print an extended help message, listing all options and any
        help text provided with them, to 'file' (default stdout).
        """
        if file is None:
            safe_print(self.format_help())
        else:
            file.write(self.format_help().encode())

    def error(self, msg):
        if self.report_errors:
            optparse.OptionParser.error(self, msg)
        else:
            raise ValueError(msg)


def parse_options(arguments, report_errors=True):
    """Support for command line options"""
    usage = _(
        """%prog [options] [files or urls]

Passing local files will add them to Variety's queue.
Passing remote URLs will make Variety fetch them to Fetched folder and place them in the queue.

To set a specific wallpaper: %prog --set /some/local/image.jpg
"""
    )

    parser = VarietyOptionParser(
        usage=usage, version="%%prog %s" % varietyconfig.get_version(), report_errors=report_errors
    )

    parser.add_option(
        "--profile",
        action="store",
        dest="profile",
        help=_(
            "Profile name or full path to the configuration folder Variety should use. "
            "If not specified, this is ~/.config/variety/. "
            "If just a name is used instead of a full path, the profile folder will be "
            "~/.config/variety-profiles/<name>. "
            "Use only when initially starting Variety - changing the profile path requires "
            "restart. Several instances of Variety can be started when using different profiles, "
            "each with its own separate configuration. This can be used for example to control "
            "several different screens or workspaces under desktop environments like XFCE which "
            "allow this. To pass commands to a running instance, pass the same --profile "
            "argument as the one it was started with in subsequent commands."
        ),
        default=None,
    )

    parser.add_option(
        "-v",
        "--verbose",
        action="count",
        dest="verbose",
        default=0,
        help=_(
            "Show logging messages (-vv to -vvvvv will profile various parts of Variety with increasing detail"
        ),
    )

    parser.add_option(
        "-q", "--quit", action="store_true", dest="quit", help=_("Make the running instance quit")
    )

    parser.add_option(
        "--get",
        "--get-wallpaper",
        "--current",
        "--show-current",
        action="store_true",
        dest="show_current",
        help=_(
            "Print the current wallpaper location. Used only when the application is already running."
        ),
    )

    parser.add_option(
        "--set",
        "--set-wallpaper",
        action="store",
        dest="set_wallpaper",
        help=_("Set the given file as wallpaper, absolute path required"),
    )

    parser.add_option(
        "-n", "--next", action="store_true", dest="next", help=_("Show Next wallpaper")
    )

    parser.add_option(
        "-p", "--previous", action="store_true", dest="previous", help=_("Show Previous wallpaper")
    )

    parser.add_option(
        "--fast-forward",
        action="store_true",
        dest="fast_forward",
        help=_("Show Next wallpaper, skipping the forward history"),
    )

    parser.add_option(
        "-t",
        "--trash",
        action="store_true",
        dest="trash",
        help=_(
            "Move current wallpaper to Trash. Used only when the application is already running."
        ),
    )

    parser.add_option(
        "-f",
        "--favorite",
        action="store_true",
        dest="favorite",
        help=_(
            "Copy current wallpaper to Favorites. Used only when the application is already running."
        ),
    )

    parser.add_option(
        "--move-to-favorites",
        action="store_true",
        dest="movefavorite",
        help=_(
            "Move current wallpaper to Favorites. Used only when the application is already running."
        ),
    )

    parser.add_option(
        "--image-origin",
        "--show-image-origin",
        "--show-origin",
        action="store_true",
        dest="showorigin",
        help=_("Open current wallpaper origin page."),
    )

    parser.add_option(
        "--pause", action="store_true", dest="pause", help=_("Pause on current image")
    )

    parser.add_option(
        "--resume", action="store_true", dest="resume", help=_("Resume regular image changes")
    )

    parser.add_option(
        "--toggle-pause",
        action="store_true",
        dest="toggle_pause",
        help=_("Toggle Pause/Resume state"),
    )

    parser.add_option(
        "--toggle-no-effects",
        action="store_true",
        dest="toggle_no_effects",
        help=_('Toggle "Show Without Effects" for current image'),
    )

    parser.add_option(
        "--quotes-next", action="store_true", dest="quotes_next", help=_("Show Next quote")
    )

    parser.add_option(
        "--quotes-previous",
        action="store_true",
        dest="quotes_previous",
        help=_("Show Previous quote"),
    )

    parser.add_option(
        "--quotes-fast-forward",
        action="store_true",
        dest="quotes_fast_forward",
        help=_("Show Next quote, skipping the forward history"),
    )

    parser.add_option(
        "--quotes-toggle-pause",
        action="store_true",
        dest="quotes_toggle_pause",
        help=_("Toggle Quotes Pause/Resume state"),
    )

    parser.add_option(
        "--quotes-save-favorite",
        action="store_true",
        dest="quotes_save_favorite",
        help=_("Save the current quote to Favorites"),
    )

    parser.add_option(
        "--history", action="store_true", dest="history", help=_("Toggle History display")
    )

    parser.add_option(
        "--downloads",
        action="store_true",
        dest="downloads",
        help=_("Toggle Recent Downloads display"),
    )

    parser.add_option(
        "--preferences",
        "--show-preferences",
        action="store_true",
        dest="preferences",
        help=_("Show Preferences dialog"),
    )

    parser.add_option(
        "--selector",
        "--show-selector",
        action="store_true",
        dest="selector",
        help=_(
            "Show manual wallpaper selector - the thumbnail bar filled with images from the active image sources"
        ),
    )

    parser.add_option(
        "--set-option",
        action="append",
        dest="set_options",
        nargs=2,
        help=_(
            "Sets and applies an option. "
            "The option names are the same that are used in Variety's config file "
            "~/.config/variety/variety.conf. "
            "Multiple options can be set in a single command. "
            "Example: 'variety --set-option icon Dark --set-option clock_enabled True'. "
            "USE WITH CAUTION: You are changing the settings file directly in an unguarded way."
        ),
    )

    options, args = parser.parse_args(arguments)

    if report_errors:
        if (options.next or options.fast_forward) and options.previous:
            parser.error(_("options --next/--fast-forward and --previous are mutually exclusive"))

        if options.trash and options.favorite:
            parser.error(_("options --trash and --favorite are mutually exclusive"))

        if options.pause and options.resume:
            parser.error(_("options --pause and --resume are mutually exclusive"))

        if (options.quotes_next or options.quotes_fast_forward) and options.quotes_previous:
            parser.error(
                _(
                    "options --quotes-next/--quotes-fast-forward and --quotes-previous are mutually exclusive"
                )
            )

    return options, args
