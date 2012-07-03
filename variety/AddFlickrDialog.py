# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

from gi.repository import Gtk, Gdk # pylint: disable=E0611
from variety.FlickrDownloader import FlickrDownloader

from variety_lib.helpers import get_builder

import gettext
from gettext import gettext as _

gettext.textdomain('variety')

import logging
import threading

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
        threading.Timer(0.1, self.on_ok).start()

    def on_ok(self):
        Gdk.threads_enter()
        self.ui.spinner.set_visible(True)
        self.ui.spinner.start()
        self.ui.error.set_label("")
        Gdk.threads_leave()

        self.tags = None
        self.user_id = None
        self.user_url = None
        self.group_id = None
        self.group_url = None

        if self.ui.tags_enabled.get_active():
            self.tags = ','.join([t.strip() for t in self.ui.tags.get_text().split(',')])

        self.error = ""

        user_url = self.ui.user_url.get_text().strip()
        if self.ui.user_enabled.get_active() and len(user_url) > 0:
            u = FlickrDownloader.obtain_userid(user_url)
            if u[0]:
                self.user_id = u[2]
                self.user_url = self.ui.user_url.get_text().replace("http://", "")
            else:
                self.error = self.error + "\n" + u[1]

        group_url = self.ui.group_url.get_text().strip()
        if self.ui.group_enabled.get_active() and len(group_url) > 0:
            g = FlickrDownloader.obtain_groupid(group_url)
            if g[0]:
                self.group_id = g[2]
                self.group_url = self.ui.group_url.get_text().replace("http://", "")
            else:
                self.error = self.error + "\n" + g[1]

        if len(self.error) > 0:
            Gdk.threads_enter()
            self.ui.error.set_label(self.error)
            self.ui.spinner.stop()
            self.ui.spinner.set_visible(False)
            Gdk.threads_leave()
        else:
            #TODO call parent callback
            self.hide()

    def on_btn_cancel_clicked(self, widget, data=None):
        """The user has elected cancel changes.

        Called before the dialog returns Gtk.ResponseType.CANCEL for run()
        """
        self.hide()

    def on_checkbox_toggled(self, widget):
        self.ui.tags.set_sensitive(self.ui.tags_enabled.get_active())
        self.ui.user_url.set_sensitive(self.ui.user_enabled.get_active())
        self.ui.group_url.set_sensitive(self.ui.group_enabled.get_active())


if __name__ == "__main__":
    dialog = AddFlickrDialog()
    dialog.show()
    Gtk.main()
