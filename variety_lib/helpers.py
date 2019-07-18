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

"""Helpers for an Ubuntu application."""
import logging
import os

from .Builder import Builder
from .varietyconfig import get_data_file


def get_builder(builder_file_name):
    """Return a fully-instantiated Gtk.Builder instance from specified ui
    file

    :param builder_file_name: The name of the builder file, without extension.
        Assumed to be in the 'ui' directory under the data path.
    """
    # Look for the ui file that describes the user interface.
    ui_filename = get_data_file("ui", "%s.ui" % (builder_file_name,))
    if not os.path.exists(ui_filename):
        ui_filename = None

    builder = Builder()
    builder.set_translation_domain("variety")
    builder.add_from_file(ui_filename)
    return builder


# Owais Lone : To get quick access to icons and stuff.
def get_media_file(media_file_name):
    media_filename = get_data_file("media", "%s" % (media_file_name,))
    if not os.path.exists(media_filename):
        media_filename = None

    return "file:///" + media_filename


def get_help_uri(page=None):
    # help_uri from source tree - default language
    here = os.path.dirname(__file__)
    help_uri = os.path.abspath(os.path.join(here, "..", "help", "C"))

    if not os.path.exists(help_uri):
        # installed so use gnome help tree - user's language
        help_uri = "variety"

    # unspecified page is the index.page
    if page is not None:
        help_uri = "%s#%s" % (help_uri, page)

    return help_uri


def show_uri(parent, link):
    from gi.repository import Gtk  # pylint: disable=E0611

    screen = parent.get_screen()
    Gtk.show_uri(screen, link, Gtk.get_current_event_time())


def alias(alternative_function_name):
    """see http://www.drdobbs.com/web-development/184406073#l9"""

    def decorator(function):
        """attach alternative_function_name(s) to function"""
        if not hasattr(function, "aliases"):
            function.aliases = []
        function.aliases.append(alternative_function_name)
        return function

    return decorator
