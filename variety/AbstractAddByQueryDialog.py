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

from gi.repository import Gtk, Gdk # pylint: disable=E0611
import threading


class AbstractAddByQueryDialog(Gtk.Dialog):
    def validate(self, query):
        """
        Example valid: return formatted(query), None
        Example invalid: return query, _('Not a proper XYZ query')
        """
        raise NotImplementedError()

    def commit(self, final_query):
        """
        Performs the actions to really add a valid query or URL to Variety
        Example: self.parent.on_add_dialog_okay(Options.SourceType.XYZ, final_query, self.edited_row)
        """
        raise NotImplementedError()

    def finish_initializing(self, builder):
        """Called when we're finished initializing.

        finish_initalizing should be called after parsing the ui definition
        and creating a AbstractAddByQueryDialog object with it in order to
        finish initializing the start of the new AbstractAddByQueryDialog
        instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self)
        self.edited_row = None

    def set_edited_row(self, edited_row):
        self.edited_row = edited_row
        self.ui.query.set_text(self.edited_row[2])

    def on_btn_ok_clicked(self, widget, data=None):
        if not len(self.ui.query.get_text().strip()):
            self.destroy()
        else:
            threading.Timer(0.1, self.ok_thread).start()

    def on_btn_cancel_clicked(self, widget, data=None):
        self.destroy()

    def ok_thread(self):
        try:
            Gdk.threads_enter()
            self.ui.message.set_visible(True)
            self.ui.buttonbox.set_sensitive(False)
            self.ui.query.set_sensitive(False)
            self.ui.spinner.set_visible(True)
            self.ui.spinner.start()
            self.ui.error.set_label("")
        finally:
            Gdk.threads_leave()

        query = self.ui.query.get_text().strip()

        final_query, invalid_msg = self.validate(query)

        try:
            Gdk.threads_enter()
            if invalid_msg:
                self.ui.buttonbox.set_sensitive(True)
                self.ui.error.set_label(invalid_msg)
                self.ui.spinner.stop()
                self.ui.query.set_sensitive(True)
                self.ui.message.set_visible(False)
                self.ui.spinner.set_visible(False)
                self.ui.query.grab_focus()
            else:
                self.commit(final_query)
                self.destroy()
        finally:
            Gdk.threads_leave()
