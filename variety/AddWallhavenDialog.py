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
import urllib
from urllib.parse import urlencode

from gi.repository import Gdk, Gtk  # pylint: disable=E0611
from variety.plugins.builtin.downloaders.WallhavenDownloader import WallhavenDownloader

from variety.Util import Util
from variety.AddConfigurableDialog import AddConfigurableDialog

from variety_lib.helpers import get_builder


class AddWallhavenDialog(AddConfigurableDialog):
    __gtype_name__ = "AddWallhavenDialog"

    def __new__(cls):
        builder = get_builder("AddWallhavenDialog")
        new_object = builder.get_object("add_wallhaven_dialog")
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called when we're finished initializing.

        finish_initalizing should be called after parsing the ui definition
        and creating a WelcomeDialog object with it in order to
        finish initializing the start of the new WelcomeDialog
        instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self)
        self.edited_row = None
        self.load_ui()

    def set_source(self, source):
        super().set_source(source)
        self.ui.use_apikey_or_not.set_label(source.get_ui_use_apikey_or_not_text())
        self.ui.apikey_instruction.set_text(source.get_ui_apikey_instruction())

    def set_edited_row(self, edited_row):
        super().set_edited_row(edited_row)
        original_location = self.edited_row[2]

        location = WallhavenDownloader(None, original_location).url
        url_parts, params = self.parse_location(location)
        if 'usekey' in params:
            self.ui.use_apikey_or_not.set_active(params['usekey'][0])
        if 'apikey' in params:
            self.ui.apikey.set_text(params['apikey'][0])

    @staticmethod
    def parse_location(location):
        if not location.startswith(("http://", "https://", "?q=")):
            location = "?q=" + location

        url_parts = urllib.parse.urlparse(location)
        params = urllib.parse.parse_qs(url_parts.query)

        return url_parts, params

    def ok_thread(self):
        def _start_ui():
            self.ui.buttonbox.set_sensitive(False)
            self.ui.message.set_visible(True)
            self.ui.query.set_sensitive(False)
            self.ui.spinner.set_visible(True)
            self.ui.spinner.start()
            self.ui.error.set_label("")
            self.ui.use_apikey_or_not.set_sensitive(False)
            self.ui.apikey.set_sensitive(False)

        Util.add_mainloop_task(_start_ui)

        query = self.ui.query.get_text().strip()
        usekey = self.ui.use_apikey_or_not.get_active()

        valition_empty_apikey = False
        invalid_msg = None
        if (usekey):
            apikey = self.ui.apikey.get_text().strip()
            if apikey is None or apikey == "":
                valition_empty_apikey = True
                invalid_msg = "Please type your apikey."
            else:
                # Append params to the original url, so that we can access those NSFW images or other settings
                if '&apikey=' not in query:
                    query = query + "&apikey=" + apikey
                if '&usekey=' not in query:
                    query = query + "&usekey=" + str(usekey)

        else:
            # query = WallhavenDownloader(None, query).url
            url_parts, queries = self.parse_location(query)
            query = self.clean_url(url_parts, queries)

        if not valition_empty_apikey:
            final_query, invalid_msg = self.validate(query)

        def _stop_ui():
            if invalid_msg:
                self.ui.error.set_label(invalid_msg)
                self.ui.spinner.stop()
                self.ui.query.set_sensitive(True)
                self.ui.message.set_visible(False)
                self.ui.spinner.set_visible(False)
                if valition_empty_apikey:
                    self.ui.apikey.grab_focus()
                else:
                    self.ui.query.grab_focus()
                self.ui.use_apikey_or_not.set_sensitive(True)
                self.ui.apikey.set_sensitive(True)
                self.ui.buttonbox.set_sensitive(True)
            else:
                self.commit(final_query)
                self.destroy()

        Util.add_mainloop_task(_stop_ui)

    def clean_location(self, location):
        """ Remove apikey and usekey from url """
        url_parts, queries = self.parse_location(location)
        return self.clean_url(url_parts, queries)

    @staticmethod
    def clean_url(url_parts, queries):
        """ Remove apikey and usekey from url """
        if len(queries) == 0:
            path = url_parts.path
            if path is not None or path != '':
                num_fields = 1 + path.count('&') + path.count(';')
                pairs = [s2 for s1 in path.split('&') for s2 in s1.split(';')]
            parsed_result = {}
            for name_value in pairs:
                nv = name_value.split('=', 1)
                name = nv[0]
                if len(nv) != 2:
                    parsed_result[name] = ''
                    continue
                if len(nv):
                    value = nv[1]
                    parsed_result[name] = value

            queries = AddWallhavenDialog.del_api_key(parsed_result)

            path_pairs = []
            for pair in queries:
                if queries[pair] != '':
                    path_pairs.append(pair + "=" + str(queries[pair]))
                else:
                    path_pairs.append(pair)

            new_path = '&'.join(path_pairs)
            url_parts = url_parts._replace(path=new_path)
            return url_parts.geturl()

        AddWallhavenDialog.del_api_key(queries)
        url_parts = url_parts._replace(query=urlencode(queries, True))
        return url_parts.geturl()

    @staticmethod
    def del_api_key(queries):
        if 'apikey' in queries:
            del queries['apikey']
        if 'usekey' in queries:
            del queries['usekey']

        return queries

    def load_ui(self):
        self.ui.apikey.set_sensitive(False)

    # Be called when click 'Use apikey?' button
    def on_use_apikey_enabled_toggled(self,  widget=None):
        self.ui.apikey.set_sensitive(self.ui.use_apikey_or_not.get_active())


if __name__ == "__main__":
    dialog = AddWallhavenDialog()
    dialog.show()
    Gtk.main()
