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

from gi.repository import Gdk, Gtk  # pylint: disable=E0611

from variety.Options import Options
from variety_lib.helpers import get_builder

logger = logging.getLogger("variety")


class AddSourceDialog(Gtk.Dialog):
    __gtype_name__ = "AddSourceDialog"

    def __new__(cls):
        builder = get_builder("AddSourceDialog")
        new_object = builder.get_object("add_source_dialog")
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        self.builder = builder
        self.ui = builder.get_ui(self)

    def on_add_images(self, widget, data=None):
        self.on_close()
        self.parent.on_add_images()

    def on_add_folders(self, widget, data=None):
        self.on_close()
        self.parent.on_add_folders(source_type=Options.SourceType.FOLDER)

    def on_add_albums_filename(self, widget, data=None):
        self.on_close()
        self.parent.on_add_folders(source_type=Options.SourceType.ALBUM_FILENAME)

    def on_add_albums_date(self, widget, data=None):
        self.on_close()
        self.parent.on_add_folders(source_type=Options.SourceType.ALBUM_DATE)

    def on_add_flickr(self, widget, data=None):
        self.on_close()
        self.parent.on_add_flickr()

    def on_add_wallhaven(self, widget, data=None):
        self.on_close()
        self.parent.on_add_wallhaven()

    def on_add_reddit(self, widget, data=None):
        self.on_close()
        self.parent.on_add_reddit()

    def on_add_mediarss(self, widget, data=None):
        self.on_close()
        self.parent.on_add_mediarss()

    def on_close(self, widget=None, data=None):
        self.destroy()
        self.parent.dialog = None


if __name__ == "__main__":
    dialog = AddSourceDialog()
    dialog.show()
    Gtk.main()
