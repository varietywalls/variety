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

from gi.repository import Gtk, Gdk # pylint: disable=E0611
from variety.WallbaseDownloader import WallbaseDownloader

from variety_lib.helpers import get_builder

import gettext
from gettext import gettext as _
gettext.textdomain('variety')

import threading
import urllib

class AddWallbaseDialog(Gtk.Dialog):
    __gtype_name__ = "AddWallbaseDialog"

    def __new__(cls):
        """Special static method that's automatically called by Python when 
        constructing a new instance of this class.
        
        Returns a fully instantiated AddWallbaseDialog object.
        """
        builder = get_builder('AddWallbaseDialog')
        new_object = builder.get_object('add_wallbase_dialog')
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called when we're finished initializing.

        finish_initalizing should be called after parsing the ui definition
        and creating a AddWallbaseDialog object with it in order to
        finish initializing the start of the new AddWallbaseDialog
        instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self)
        self.edited_row = None

    def set_edited_row(self, edited_row):
        self.edited_row = edited_row
        self.ui.query.set_text(edited_row[2])

    def on_btn_ok_clicked(self, widget, data=None):
        """The user has elected to save the changes.

        Called before the dialog returns Gtk.ResponseType.OK from run().
        """
        if not len(self.ui.query.get_text().strip()):
            self.destroy()
        else:
            threading.Timer(0.1, self.ok_thread).start()

    def show_spinner(self):
        try:
            Gdk.threads_enter()
            self.ui.query.set_sensitive(False)
            self.ui.buttonbox.set_sensitive(False)
            self.ui.message.set_visible(True)
            self.ui.spinner.set_visible(True)
            self.ui.spinner.start()
            self.ui.error.set_label("")
        finally:
            Gdk.threads_leave()

    def ok_thread(self):
        search = self.ui.query.get_text().strip()

        error = ""
        self.show_spinner()
        if not WallbaseDownloader.validate(search):
            error = _("No images found")

        try:
            Gdk.threads_enter()

            self.ui.query.set_sensitive(True)
            self.ui.buttonbox.set_sensitive(True)
            self.ui.spinner.stop()
            self.ui.spinner.set_visible(False)
            self.ui.message.set_visible(False)

            if len(error) > 0:
                self.ui.error.set_label(error)
                self.ui.query.grab_focus()
            else:
                if len(search):
                    self.parent.on_wallbase_dialog_okay(search, self.edited_row)
                self.destroy()

        finally:
            Gdk.threads_leave()

    def on_btn_cancel_clicked(self, widget, data=None):
        """The user has elected cancel changes.

        Called before the dialog returns Gtk.ResponseType.CANCEL for run()
        """
        self.destroy()

if __name__ == "__main__":
    dialog = AddWallbaseDialog()
    dialog.show()
    Gtk.main()
