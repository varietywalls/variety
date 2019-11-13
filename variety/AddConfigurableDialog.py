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

from variety.AbstractAddByQueryDialog import AbstractAddByQueryDialog
from variety_lib.helpers import get_builder


class AddConfigurableDialog(AbstractAddByQueryDialog):
    __gtype_name__ = "AddConfigurableDialog"

    def __new__(cls):
        builder = get_builder("AddConfigurableDialog")
        new_object = builder.get_object("add_configurable_dialog")
        new_object.finish_initializing(builder)
        return new_object

    def set_source(self, source):
        self.source = source
        self.set_title("Variety - add {} source".format(source.get_source_name()))
        self.ui.title.set_text(source.get_source_name())
        self.ui.instruction.set_markup(source.get_ui_instruction())
        self.ui.short_instruction.set_markup(source.get_ui_short_instruction())

    def validate(self, query):
        return self.source.validate(query)

    def commit(self, final_query):
        if len(final_query):
            self.parent.on_add_dialog_okay(
                self.source.get_source_type(), final_query, self.edited_row
            )
