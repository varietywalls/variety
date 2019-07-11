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
import threading
import urllib.parse

from gi.repository import Gdk, Gtk  # pylint: disable=E0611

from variety import _
from variety.FlickrDownloader import FlickrDownloader
from variety.Options import Options
from variety_lib.helpers import get_builder

logger = logging.getLogger("variety")


class AddFlickrDialog(Gtk.Dialog):
    __gtype_name__ = "AddFlickrDialog"

    def __new__(cls):
        """Special static method that's automatically called by Python when 
        constructing a new instance of this class.
        
        Returns a fully instantiated AddFlickrDialog object.
        """
        builder = get_builder("AddFlickrDialog")
        new_object = builder.get_object("add_flickr_dialog")
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called when we're finished initializing.

        finish_initalizing should be called after parsing the ui definition
        and creating a AddFlickrDialog object with it in order to
        finish initializing the start of the new AddFlickrDialog
        instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self)
        self.edited_row = None

    def set_edited_row(self, edited_row):
        self.edited_row = edited_row

        location = edited_row[2]
        s = location.split(";")
        params = {}
        for x in s:
            if len(x) and x.find(":") > 0:
                k, v = x.split(":")
                params[k.lower()] = urllib.parse.unquote_plus(v)

        if "text" in params:
            self.ui.text.set_text(params["text"])

        if "tags" in params:
            self.ui.tags.set_text(params["tags"])

        if "user" in params:
            if "://" not in params["user"]:
                params["user"] = "https://" + params["user"]
            self.ui.user_url.set_text(params["user"])

        if "group" in params:
            if "://" not in params["group"]:
                params["group"] = "https://" + params["group"]
            self.ui.group_url.set_text(params["group"])

    def on_btn_ok_clicked(self, widget, data=None):
        """The user has elected to save the changes.

        Called before the dialog returns Gtk.ResponseType.OK from run().
        """
        threading.Timer(0, self.ok_thread).start()

    def show_spinner(self):
        try:
            Gdk.threads_enter()
            self.ui.buttonbox.set_sensitive(False)
            self.ui.message.set_visible(True)
            self.ui.spinner.set_visible(True)
            self.ui.spinner.start()
            self.ui.error.set_label("")
        finally:
            Gdk.threads_leave()

    def ok_thread(self):
        search = ""

        if len(self.ui.tags.get_text().strip()):
            search += (
                "tags:"
                + ",".join(
                    [urllib.parse.quote_plus(t.strip()) for t in self.ui.tags.get_text().split(",")]
                )
                + ";"
            )

        if len(self.ui.text.get_text().strip()):
            search += "text:" + urllib.parse.quote_plus(self.ui.text.get_text().strip()) + ";"

        self.error = ""

        user_url = self.ui.user_url.get_text().strip()
        if len(user_url) > 0:
            self.show_spinner()
            u = FlickrDownloader.obtain_userid(user_url)
            if u[0]:
                search += (
                    "user:"
                    + self.ui.user_url.get_text().replace("http://", "").replace("https://", "")
                    + ";"
                )
                search += "user_id:" + u[2] + ";"
            else:
                self.error = self.error + "\n" + u[1]

        group_url = self.ui.group_url.get_text().strip()
        if len(group_url) > 0:
            self.show_spinner()
            g = FlickrDownloader.obtain_groupid(group_url)
            if g[0]:
                search += (
                    "group:"
                    + self.ui.group_url.get_text().replace("http://", "").replace("https://", "")
                    + ";"
                )
                search += "group_id:" + g[2]
            else:
                self.error = self.error + "\n" + g[1]

        if not len(self.error) and len(search) > 0:
            self.show_spinner()
            if FlickrDownloader.count_search_results(search) <= 0:
                self.error = _("No images found")

        try:
            Gdk.threads_enter()

            self.ui.buttonbox.set_sensitive(True)
            self.ui.spinner.stop()
            self.ui.spinner.set_visible(False)
            self.ui.message.set_visible(False)

            if len(self.error) > 0:
                self.ui.error.set_label(self.error)
                for entry in (self.ui.text, self.ui.tags, self.ui.user_url, self.ui.group_url):
                    if entry.get_text().strip():
                        entry.grab_focus()
                        break
            else:
                if len(search):
                    self.parent.on_add_dialog_okay(
                        Options.SourceType.FLICKR, search, self.edited_row
                    )
                self.destroy()

        finally:
            Gdk.threads_leave()

    def on_btn_cancel_clicked(self, widget, data=None):
        """The user has elected cancel changes.

        Called before the dialog returns Gtk.ResponseType.CANCEL for run()
        """
        self.destroy()


if __name__ == "__main__":
    dialog = AddFlickrDialog()
    dialog.show()
    Gtk.main()
