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

from variety.AddConfigurableDialog import AddConfigurableDialog
from variety_lib.helpers import get_builder


class AddWallhavenDialog(AddConfigurableDialog):
    __gtype_name__ = "AddWallhavenDialog"

    def __new__(cls, variety):
        builder = get_builder("AddWallhavenDialog")
        new_object = builder.get_object("add_wallhaven_dialog")
        new_object.finish_initializing(builder)
        new_object.options = variety.options
        new_object.ui.apikey.set_text((variety.options.wallhaven_api_key or "").strip())
        return new_object

    def validate(self, query):
        api_key = self.ui.apikey.get_text().strip()
        query, msg = self.source.validate(query, api_key=api_key)
        if not msg:
            # valid query - persist the API key for future use
            self.options.wallhaven_api_key = api_key
            self.options.write()
        return query, msg

    @staticmethod
    def parse_location(location):
        url_parts = urllib.parse.urlparse(location)
        return urllib.parse.parse_qs(url_parts.query)
