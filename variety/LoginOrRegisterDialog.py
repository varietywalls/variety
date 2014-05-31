# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

from gi.repository import Gtk  # pylint: disable=E0611
from variety.Util import Util
from variety_lib.helpers import get_builder

import gettext
from gettext import gettext as _

gettext.textdomain('variety')


class LoginOrRegisterDialog(Gtk.Dialog):
    __gtype_name__ = "LoginOrRegisterDialog"

    def __new__(cls):
        """Special static method that's automatically called by Python when 
        constructing a new instance of this class.
        
        Returns a fully instantiated LoginOrRegisterDialog object.
        """
        builder = get_builder('LoginOrRegisterDialog')
        new_object = builder.get_object('login_or_register_dialog')
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called when we're finished initializing.

        finish_initalizing should be called after parsing the ui definition
        and creating a LoginOrRegisterDialog object with it in order to
        finish initializing the start of the new LoginOrRegisterDialog
        instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.parent = None
        self.ui = builder.get_ui(self)

    def on_btn_login_clicked(self, widget=None):
        print self.parent.parent.VARIETY_API_URL
        result = Util.fetch_json(self.parent.parent.VARIETY_API_URL + '/login',
                                 {'username': self.ui.login_username.get_text(),
                                  'password': self.ui.login_password.get_text()})
        if 'error' in result:
            self.ui.login_error.set_text(_(result['error']))
            self.ui.login_error.set_visible(True)

    def on_btn_login_clicked(self, widget=None):
        result = Util.fetch_json(self.parent.parent.VARIETY_API_URL + '/login',
                                 {'username': self.ui.login_username.get_text(),
                                  'password': self.ui.login_password.get_text()})
        if 'error' in result:
            self.ui.login_error.set_text(_(result['error']))
            self.ui.login_error.set_visible(True)
        else:
            self.parent.parent.set_smart_user(result)
            self.destroy()

    def on_btn_register_clicked(self, widget=None):
        if self.ui.register_password.get_text() != self.ui.register_password_confirm.get_text():
            self.ui.register_error.set_text(_('Passwords must match'))
            self.ui.register_error.set_visible(True)
            return

        result = Util.fetch_json(self.parent.parent.VARIETY_API_URL + '/register',
                                 {'username': self.ui.register_username.get_text(),
                                  'password': self.ui.register_password.get_text(),
                                  'email': self.ui.register_email.get_text()})
        if 'error' in result:
            self.ui.register_error.set_text(_(result['error']))
            self.ui.register_error.set_visible(True)
        else:
            self.parent.parent.set_smart_user(result)
            self.destroy()


if __name__ == "__main__":
    dialog = LoginOrRegisterDialog()
    dialog.show()
    Gtk.main()
