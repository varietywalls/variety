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

        self.on_radio_toggled()
        self.ui.sfw.set_active(0)
        self.ui.manga.set_active(2)
        self.ui.favs_count.set_active(1)

        self.ui.radio_all.set_active(True)
        self.ui.order_random.set_active(True)

    def set_edited_row(self, edited_row):
        self.edited_row = edited_row

        location = edited_row[2]
        s = location.split(';')
        params = {}
        for x in s:
            if len(x) and x.find(':') > 0:
                k, v = x.split(':')
                params[k.lower()] = urllib.unquote_plus(v)

        if params["type"] == "text":
            self.ui.radio_text.set_active(True)
            self.ui.query.set_text(urllib.unquote_plus(params["query"]))
        elif params["type"] == "color":
            self.ui.radio_color.set_active(True)
            c = map(int, params["color"].split('/'))
            self.ui.color.set_color(Gdk.Color(red = c[0] * 256, green = c[1] * 256, blue = c[2] * 256))
        else:
            self.ui.radio_all.set_active(True)

        if params["order"] == "random":
            self.ui.order_random.set_active(True)
        else:
            self.ui.order_favs.set_active(True)
            for i, x in enumerate(self.ui.favs_count.get_model()):
                if int(x[0]) >= int(params["favs_count"]):
                    self.ui.favs_count.set_active(i)
                    break

        if params["nsfw"] == "110":
            self.ui.sfw.set_active(2)
        elif params["nsfw"] == "010":
            self.ui.sfw.set_active(1)
        else:
            self.ui.sfw.set_active(0)

        if params["board"] == "2":
            self.ui.manga.set_active(0)
        elif params["board"] == "1":
            self.ui.manga.set_active(1)
        else:
            self.ui.manga.set_active(2)

    def on_btn_ok_clicked(self, widget, data=None):
        """The user has elected to save the changes.

        Called before the dialog returns Gtk.ResponseType.OK from run().
        """
        threading.Timer(0.1, self.ok_thread).start()

    def on_radio_toggled(self, widget = None):
        pass
#        self.ui.query.set_sensitive(self.ui.radio_text.get_active())
#        self.ui.color.set_sensitive(self.ui.radio_color.get_active())
#        self.ui.favs_count.set_sensitive(self.ui.order_favs.get_active())

    def on_color_set(self, widget = None):
        self.ui.radio_color.set_active(True)

    def on_query_changed(self, widget = None):
        self.ui.radio_text.set_active(True)

    def on_favs_count_changed(self, widget = None):
        self.ui.order_favs.set_active(True)

    def show_spinner(self):
        Gdk.threads_enter()
        self.ui.buttonbox.set_sensitive(False)
        self.ui.message.set_visible(True)
        self.ui.spinner.set_visible(True)
        self.ui.spinner.start()
        self.ui.error.set_label("")
        Gdk.threads_leave()

    def ok_thread(self):
        search = ""

        if self.ui.radio_text.get_active():
            search += "type:text;"
            query = self.ui.query.get_text().strip()
            if not len(query):
                Gdk.threads_enter()
                self.ui.query_error.set_visible(True)
                Gdk.threads_leave()
                return
            search += "query:" + urllib.quote_plus(query) + ";"

        elif self.ui.radio_color.get_active():
            search += "type:color;"
            c = self.ui.color.get_color()
            color = "%d/%d/%d" % (c.red // 256, c.green // 256, c.blue // 256)
            search += "color:" + color + ";"

        else:
            search += "type:all;"

        if self.ui.order_favs.get_active():
            search += "order:favs;favs_count:%d;" % int(self.ui.favs_count.get_active_text())
        else:
            search += "order:random;"

        if self.ui.sfw.get_active() == 0:
            search += "nsfw:100;"
        elif self.ui.sfw.get_active() == 1:
            search += "nsfw:010;"
        else:
            search += "nsfw:110;"

        if self.ui.manga.get_active() == 0:
            search += "board:2"
        elif self.ui.manga.get_active() == 1:
            search += "board:1"
        else:
            search += "board:12"

        self.error = ""
        self.show_spinner()
        if not WallbaseDownloader.validate(search):
            self.error = _("No images found")

        Gdk.threads_enter()

        self.ui.buttonbox.set_sensitive(True)
        self.ui.spinner.stop()
        self.ui.spinner.set_visible(False)
        self.ui.message.set_visible(False)

        if len(self.error) > 0:
            self.ui.error.set_label(self.error)
            self.ui.query.grab_focus()
        else:
            if len(search):
                self.parent.on_wallbase_dialog_okay(search, self.edited_row)
            self.destroy()

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
