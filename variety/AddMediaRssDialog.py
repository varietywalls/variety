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

from gi.repository import Gtk # pylint: disable=E0611
from variety.AbstractAddByQueryDialog import AbstractAddByQueryDialog
from variety.MediaRssDownloader import MediaRssDownloader
from variety.Options import Options

from variety_lib.helpers import get_builder

from variety import _


class AddMediaRssDialog(AbstractAddByQueryDialog):
    __gtype_name__ = "AddMediaRssDialog"

    def __new__(cls):
        builder = get_builder('AddMediaRssDialog')
        new_object = builder.get_object('add_media_rss_dialog')
        new_object.finish_initializing(builder)
        return new_object

    def validate(self, url):
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        valid = MediaRssDownloader.validate(url)
        return url, None if valid else _("This does not seem to be a valid Media RSS feed URL or there is no content there.")

    def commit(self, final_url):
        self.parent.on_add_dialog_okay(Options.SourceType.MEDIA_RSS, final_url, self.edited_row)


if __name__ == "__main__":
    dialog = AddMediaRssDialog()
    dialog.show()
    Gtk.main()
