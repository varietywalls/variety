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

from gi.repository import Gtk  # pylint: disable=E0611

from variety import _
from variety.AbstractAddByQueryDialog import AbstractAddByQueryDialog
from variety.Options import Options
from variety.RedditDownloader import RedditDownloader
from variety_lib.helpers import get_builder


class AddRedditDialog(AbstractAddByQueryDialog):
    __gtype_name__ = "AddRedditDialog"

    def __new__(cls):
        builder = get_builder("AddRedditDialog")
        new_object = builder.get_object("add_reddit_dialog")
        new_object.finish_initializing(builder)
        return new_object

    def validate(self, query):
        if not "/" in query:
            query = "https://www.reddit.com/r/%s" % query
        else:
            if not query.startswith("http://") and not query.startswith("https://"):
                query = "https://" + query
            if not "//reddit.com" in query and not "//www.reddit.com" in query:
                return query, False, _("This does not seem to be a valid Reddit URL")

        valid = RedditDownloader.validate(query, self.parent)
        return (query, None if valid else _("We could not find any image submissions there."))

    def commit(self, final_url):
        if final_url:
            self.parent.on_add_dialog_okay(Options.SourceType.REDDIT, final_url, self.edited_row)


if __name__ == "__main__":
    dialog = AddRedditDialog()
    dialog.show()
    Gtk.main()
