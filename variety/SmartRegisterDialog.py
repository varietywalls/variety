# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

from gi.repository import Gtk # pylint: disable=E0611

from variety_lib.helpers import get_builder

import gettext
from gettext import gettext as _
gettext.textdomain('variety')

class SmartRegisterDialog(Gtk.Dialog):
    __gtype_name__ = "SmartRegisterDialog"

    def __new__(cls):
        """Special static method that's automatically called by Python when 
        constructing a new instance of this class.
        
        Returns a fully instantiated SmartRegisterDialog object.
        """
        builder = get_builder('SmartRegisterDialog')
        new_object = builder.get_object('smart_register_dialog')
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called when we're finished initializing.

        finish_initalizing should be called after parsing the ui definition
        and creating a SmartRegisterDialog object with it in order to
        finish initializing the start of the new SmartRegisterDialog
        instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self)
        self.result = "anonymous"

    def on_anonymous_clicked(self, widget):
        self.result = "anonymous"

    def on_login_clicked(self, widget):
        self.result = "login"

    def on_register_clicked(self, widget):
        self.result = "register"


if __name__ == "__main__":
    dialog = SmartRegisterDialog()
    dialog.show()
    Gtk.main()
