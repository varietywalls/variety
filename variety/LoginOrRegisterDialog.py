# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

from gi.repository import Gtk, GObject  # pylint: disable=E0611
import logging
import threading
import urllib2
from variety.Util import Util
from variety.Smart import Smart
from variety_lib.helpers import get_builder

import gettext
from gettext import gettext as _

gettext.textdomain('variety')
logger = logging.getLogger('variety')


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
        self.smart = None
        self.ui = builder.get_ui(self)

    def show_login_error(self, msg):
        def _go():
            self.ui.login_error.set_text(msg)
            self.ui.login_error.set_visible(True)
            self.ui.login_spinner.set_visible(False)
            self.ui.login_spinner.stop()
        GObject.idle_add(_go)

    def show_register_error(self, msg):
        def _go():
            self.ui.register_error.set_text(msg)
            self.ui.register_error.set_visible(True)
            self.ui.register_spinner.set_visible(False)
            self.ui.register_spinner.stop()
        GObject.idle_add(_go)

    def ajax(self, url, data, error_msg_handler):
        try:
            return Util.fetch_json(url, data)
        except urllib2.HTTPError, e:
            logger.exception('HTTPError for ' + url)
            error_msg_handler(_('Oops, server returned error (%s)') % e.code)
            raise

        except urllib2.URLError:
            logger.exception('Connection error for ' + url)
            error_msg_handler(_('Could not connect to server'))
            raise

    def on_btn_login_clicked(self, widget=None):
        self.ui.login_error.set_visible(False)
        self.ui.login_spinner.set_visible(True)
        self.ui.login_spinner.start()

        def _go():
            result = self.ajax(Smart.API_URL + '/login',
                               {'username': self.ui.login_username.get_text(),
                                'password': self.ui.login_password.get_text()},
                               self.show_login_error)

            def _update():
                if 'error' in result:
                    self.show_login_error(_(result['error']))
                else:
                    self.smart.set_user(result)
                    self.destroy()
            GObject.idle_add(_update)
        threading.Timer(0.1, _go).start()

    def on_btn_register_clicked(self, widget=None):
        self.ui.register_error.set_visible(False)
        self.ui.register_spinner.set_visible(True)
        self.ui.register_spinner.start()

        if self.ui.register_password.get_text() != self.ui.register_password_confirm.get_text():
            self.show_register_error(_('Passwords must match'))
            return

        user = {'username': self.ui.register_username.get_text(),
                'password': self.ui.register_password.get_text(),
                'password-confirm': self.ui.register_password_confirm.get_text(),
                'email': self.ui.register_email.get_text()}

        # If the current user is anonymous, use its existing data, do not register a completely new user:
        if self.smart.user.get("username") is None:
            user.update({'id': self.smart.user['id'], 'authkey': self.smart.user['authkey']})

        def _go():
            result = self.ajax(Smart.API_URL + '/register', user, self.show_register_error)

            def _update():
                if 'error' in result:
                    self.show_register_error(_(result['error']))
                else:
                    self.smart.set_user(result)
                    self.destroy()
            GObject.idle_add(_update)
        threading.Timer(0.1, _go).start()


if __name__ == "__main__":
    dialog = LoginOrRegisterDialog()
    dialog.show()
    Gtk.main()
