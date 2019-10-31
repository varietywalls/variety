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
import random

from data.plugins.downloaders.RedditDownloader import RedditDownloader
from variety.plugins.downloaders.ConfigurableImageSource import ConfigurableImageSource
from variety.Util import _

random.seed()


logger = logging.getLogger("variety")


class RedditSource(ConfigurableImageSource):
    @classmethod
    def get_info(cls):
        return {
            "name": "RedditSource",
            "description": _("Configurable source for fetching images from Reddit"),
            "author": "Peter Levi",
            "version": "0.1",
        }

    def get_source_type(self):
        return "reddit"

    def get_source_name(self):
        return "Reddit"

    def get_ui_instruction(self):
        return _(
            "Enter the name of a subreddit or paste the full URL of a subreddit or a "
            "<a href='http://reddit.com'>Reddit</a> user. You may specify sort order and time "
            "period if you wish. Variety will use posts to direct images or to Imgur pages "
            "within the first 100 submissions returned by Reddit.\n\n"
            "Example: You may specify simply 'comics' or "
            "<a href='http://www.reddit.com/r/comics'>http://www.reddit.com/r/comics</a>\n"
            "Example: Top posts from the month: "
            "<a href='http://www.reddit.com/r/comics/top/?sort=top&amp;t=month'>http://www.reddit.com/r/comics/top/?sort=top&amp;t=month</a>"
        )

    def get_ui_short_instruction(self):
        return _("URL or name of a subreddit: ")

    def get_ui_short_description(self):
        return _("Fetch images from a given subreddit or user")

    def validate(self, query):
        logger.info(lambda: "Validating Reddit query " + query)
        if not "/" in query:
            query = "https://www.reddit.com/r/%s" % query
        try:
            if not query.startswith("http://") and not query.startswith("https://"):
                query = "http://" + query

            if not "//reddit.com" in query and not "//www.reddit.com" in query:
                return False, _("This does not seem to be a valid Reddit URL")

            dl = RedditDownloader(self, query)
            queue = dl.fill_queue()
            return (
                query,
                None if len(queue) > 0 else _("We could not find any image submissions there."),
            )
        except Exception:
            logger.exception(
                lambda: "Error while validating URL, probably no image posts for this URL"
            )
            return query, _("We could not find any image submissions there.")

    def create_downloader(self, config, full_descriptor=None):
        return RedditDownloader(self, config)
