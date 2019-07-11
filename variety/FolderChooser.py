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

import logging
import os.path

from gi.repository import Gtk

from variety import _
from variety.Util import Util

logger = logging.getLogger("variety")


class FolderChooser:
    def __init__(self, button, on_change=None):
        self.button = button
        self.on_change = on_change
        self.folder = None
        self.chooser = None
        self.box = Gtk.Box(Gtk.Orientation.HORIZONTAL)
        self.label = Gtk.Label()
        self.image = Gtk.Image()
        self.image.set_margin_left(2)
        self.image.set_margin_right(5)
        self.image.set_from_icon_name("folder", Gtk.IconSize.MENU)
        self.box.add(self.image)
        self.box.add(self.label)
        self.box.set_margin_right(2)
        if self.button.get_child():
            self.button.get_child().destroy()
        self.button.add(self.box)
        self.button.show_all()
        self.button.connect("clicked", self.browse)

    def destroy(self):
        if self.chooser:
            self.chooser.destroy()

    def get_folder(self):
        return self.folder

    def set_folder(self, folder):
        self.folder = os.path.normpath(folder)
        self.image.set_from_icon_name(Util.get_file_icon_name(self.folder), Gtk.IconSize.MENU)
        self.label.set_text(Util.collapseuser(self.folder))
        self.button.set_tooltip_text(self.folder)

    def set_sensitive(self, sensitive):
        self.button.set_sensitive(sensitive)

    def browse(self, widget=None):
        try:
            self.chooser = Gtk.FileChooserDialog(
                _("Choose a folder"),
                parent=self.button.get_toplevel(),
                action=Gtk.FileChooserAction.SELECT_FOLDER,
                buttons=[_("Cancel"), Gtk.ResponseType.CANCEL, _("OK"), Gtk.ResponseType.OK],
            )
            self.chooser.set_filename(self.folder)
            self.chooser.set_select_multiple(False)
            self.chooser.set_local_only(False)

            if self.chooser.run() == Gtk.ResponseType.OK:
                self.set_folder(self.chooser.get_filename())
                try:
                    if self.on_change:
                        self.on_change()
                except Exception:
                    logger.exception(lambda: "Exception during FolderChooser on_change:")
        finally:
            if self.chooser:
                try:
                    self.chooser.destroy()
                    self.chooser = None
                except Exception:
                    logger.exception(lambda: "Exception during FolderChooser destroying:")
