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
from variety.FlickrDownloader import FlickrDownloader

from variety_lib.helpers import get_builder

import gettext
from gettext import gettext as _

gettext.textdomain('variety')

import logging
import threading
import urllib

logger = logging.getLogger('variety')

class AddFlickrDialog(Gtk.Dialog):
    __gtype_name__ = "AddFlickrDialog"

    def __new__(cls):
        """Special static method that's automatically called by Python when 
        constructing a new instance of this class.
        
        Returns a fully instantiated AddFlickrDialog object.
        """
        builder = get_builder('AddFlickrDialog')
        new_object = builder.get_object('add_flickr_dialog')
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

    def on_btn_ok_clicked(self, widget, data=None):
        """The user has elected to save the changes.

        Called before the dialog returns Gtk.ResponseType.OK from run().
        """
        threading.Timer(0.1, self.ok_thread).start()

    def ok_thread(self):
        Gdk.threads_enter()
        self.ui.spinner.set_visible(True)
        self.ui.spinner.start()
        self.ui.error.set_label("")
        Gdk.threads_leave()

        search = ""

        if len(self.ui.tags.get_text().strip()):
            search +=  "tags:" + ','.join([urllib.quote_plus(t.strip()) for t in self.ui.tags.get_text().split(',')]) + ";"

        if len(self.ui.text.get_text().strip()):
            search +=  "text:" + urllib.quote_plus(self.ui.text.get_text().strip()) +";"

        self.error = ""

        user_url = self.ui.user_url.get_text().strip()
        if len(user_url) > 0:
            u = FlickrDownloader.obtain_userid(user_url)
            if u[0]:
                search += "user:" + self.ui.user_url.get_text().replace("http://", "") + ";"
                search += "user_id:" + u[2] + ";"
            else:
                self.error = self.error + "\n" + u[1]

        group_url = self.ui.group_url.get_text().strip()
        if len(group_url) > 0:
            g = FlickrDownloader.obtain_groupid(group_url)
            if g[0]:
                search += "group:" + self.ui.group_url.get_text().replace("http://", "") + ";"
                search += "group_id:" + g[2]
            else:
                self.error = self.error + "\n" + g[1]

        Gdk.threads_enter()

        if len(self.error) > 0:
            self.ui.error.set_label(self.error)
            self.ui.spinner.stop()
            self.ui.spinner.set_visible(False)
        else:
            if len(search):
                self.parent.on_flickr_dialog_okay(search)
            self.destroy()

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
