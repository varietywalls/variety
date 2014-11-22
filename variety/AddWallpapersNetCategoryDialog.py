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

from gi.repository import Gtk # pylint: disable=E0611
from variety.AbstractAddByQueryDialog import AbstractAddByQueryDialog

from variety_lib.helpers import get_builder
from variety.WallpapersNetDownloader import WallpapersNetDownloader

from variety import _


class AddWallpapersNetCategoryDialog(AbstractAddByQueryDialog):
    __gtype_name__ = "AddWallpapersNetCategoryDialog"

    def __new__(cls):
        builder = get_builder('AddWallpapersNetCategoryDialog')
        new_object = builder.get_object('add_wallpapers_net_category_dialog')
        new_object.finish_initializing(builder)
        return new_object

    def validate(self, url):
        if not url.startswith("http://"):
            url = "http://" + url
        valid = WallpapersNetDownloader.validate(url)
        return url, None if valid else _("Could not find wallpapers there. Please check the URL.")

    def commit(self, url):
        if url:
            self.parent.on_wn_dialog_okay(url, self.edited_row)


if __name__ == "__main__":
    dialog = AddWallpapersNetCategoryDialog()
    dialog.show()
    Gtk.main()
