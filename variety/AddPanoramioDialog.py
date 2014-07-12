# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE
import json

import logging
from gi.repository import Gtk, WebKit, GObject # pylint: disable=E0611
from variety_lib.helpers import get_builder
from variety import _, _u
from variety_lib import varietyconfig

logger = logging.getLogger('variety')

class AddPanoramioDialog(Gtk.Dialog):
    __gtype_name__ = "AddPanoramioDialog"

    def __new__(cls):
        """Special static method that's automatically called by Python when 
        constructing a new instance of this class.
        
        Returns a fully instantiated AddPanoramioDialog object.
        """
        builder = get_builder('AddPanoramioDialog')
        new_object = builder.get_object('add_panoramio_dialog')
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called when we're finished initializing.

        finish_initalizing should be called after parsing the ui definition
        and creating a AddPanoramioDialog object with it in order to
        finish initializing the start of the new AddPanoramioDialog
        instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self)
        self.edited_row = None
        self.load_map()

    def set_edited_row(self, edited_row):
        self.edited_row = edited_row
        js = "setLocation('" + edited_row[2] + "')"
        self.js(js)

    def path2url(self, path):
        import urllib
        return 'file://' + urllib.pathname2url(path)

    def js(self, command):
        logger.debug('Panoramio: js(%s)' % command)
        if hasattr(self, "web_view_loaded"):
            GObject.idle_add(lambda: self.web_view.execute_script(command))
        else:
            GObject.timeout_add(100, lambda: self.js(command))

    def on_js_action(self, action, argument):
        if action == 'location':
            location = argument
            self.parent.on_panoramio_dialog_okay(location, self.edited_row)
            self.destroy()

    def load_map(self):
        with open(varietyconfig.get_data_file('panoramio/panoramio.html')) as f:
            html = f.read()

        self.web_view = WebKit.WebView()

        def nav(wv, command):
            if command:
                logger.info('Received command: ' + command)
                command = command[command.index('|') + 1:]
                index = command.index(':')
                action = command[:index]
                argument = command[index + 1:]
                self.on_js_action(action, argument)
        self.web_view.connect("status-bar-text-changed", nav)

        def _loaded(wv, data):
            self.web_view_loaded = True
        self.web_view.connect('document-load-finished', _loaded)

        self.web_view.load_string(html, "text/html", "UTF-8", self.path2url(varietyconfig.get_data_path()) + '/panoramio/')
        self.web_view.set_visible(True)
        self.ui.scrolledwindow.add(self.web_view)

    def on_btn_ok_clicked(self, widget, data=None):
        self.js('reportLocation()')

    def on_btn_cancel_clicked(self, widget, data=None):
        self.destroy()


if __name__ == "__main__":
    dialog = AddPanoramioDialog()
    dialog.show()
    Gtk.main()
