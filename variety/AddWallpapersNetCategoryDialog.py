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

from gi.repository import Gtk, Gdk # pylint: disable=E0611

from variety_lib.helpers import get_builder
from variety.WallpapersNetDownloader import WallpapersNetDownloader

import threading
import gettext
from gettext import gettext as _
gettext.textdomain('variety')

class AddWallpapersNetCategoryDialog(Gtk.Dialog):
    __gtype_name__ = "AddWallpapersNetCategoryDialog"

    def __new__(cls):
        """Special static method that's automatically called by Python when
        constructing a new instance of this class.
        
        Returns a fully instantiated AddWallpapersNetCategoryDialog object.
        """
        builder = get_builder('AddWallpapersNetCategoryDialog')
        new_object = builder.get_object('add_wallpapers_net_category_dialog')
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called when we're finished initializing.

        finish_initalizing should be called after parsing the ui definition
        and creating a AddWallpapersNetCategoryDialog object with it in order to
        finish initializing the start of the new AddWallpapersNetCategoryDialog
        instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self)
        self.edited_row = None

    def set_edited_row(self, edited_row):
        self.edited_row = edited_row
        self.ui.url.set_text(self.edited_row[2])

    def on_btn_ok_clicked(self, widget, data=None):
        """The user has elected to save the changes.

        Called before the dialog returns Gtk.ResponseType.OK from run().
        """
        if not len(self.ui.url.get_text().strip()):
            self.destroy()
        else:
            threading.Timer(0.1, self.ok_thread).start()

    def ok_thread(self):
        Gdk.threads_enter()
        self.ui.message.set_visible(True)
        self.ui.url.set_sensitive(False)
        self.ui.spinner.set_visible(True)
        self.ui.spinner.start()
        self.ui.error.set_label("")
        Gdk.threads_leave()

        url = self.ui.url.get_text().strip()
        if not url.startswith("http://"):
            url = "http://" + url
        valid = WallpapersNetDownloader.validate(url)

        Gdk.threads_enter()
        if not valid:
            self.ui.error.set_label("Could not find wallpapers there. Please check the URL.")
            self.ui.spinner.stop()
            self.ui.url.set_sensitive(True)
            self.ui.message.set_visible(False)
            self.ui.spinner.set_visible(False)
        else:
            self.parent.on_wn_dialog_okay(url, self.edited_row)
            self.destroy()
        Gdk.threads_leave()

    def on_btn_cancel_clicked(self, widget, data=None):
        """The user has elected cancel changes.

        Called before the dialog returns Gtk.ResponseType.CANCEL for run()
        """
        self.destroy()


if __name__ == "__main__":
    dialog = AddWallpapersNetCategoryDialog()
    dialog.show()
    Gtk.main()
