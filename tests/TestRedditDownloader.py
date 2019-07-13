#!/usr/bin/python3
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

import unittest

from tests.TestDownloader import test_download_one_for
from variety.AttrDict import AttrDict
from variety.RedditDownloader import RedditDownloader


class TestRedditDownloader(unittest.TestCase):
    def test_download_one(self):
        test_download_one_for(self, RedditDownloader(None, "http://www.reddit.com/r/AutumnPorn/"))

    def test_build_json_url(self):
        self.assertEqual(
            "http://www.reddit.com/r/comics/.json?limit=100",
            RedditDownloader.build_json_url("http://www.reddit.com/r/comics/"),
        )

        self.assertEqual(
            "http://www.reddit.com/r/comics/top/.json?limit=100",
            RedditDownloader.build_json_url("http://www.reddit.com/r/comics/top/"),
        )

        self.assertEqual(
            "http://www.reddit.com/r/comics/top/.json?sort=top&t=week&limit=100",
            RedditDownloader.build_json_url("http://www.reddit.com/r/comics/top/?sort=top&t=week"),
        )

    def test_validate(self):
        parent = AttrDict()

        parent.options.safe_mode = True
        self.assertTrue(RedditDownloader.validate("http://www.reddit.com/r/comics", parent))
        self.assertFalse(RedditDownloader.validate("http://www.reddit.com/r/nsfw/", parent))

        parent.options.safe_mode = False
        self.assertTrue(RedditDownloader.validate("http://www.reddit.com/r/comics", parent))
        self.assertTrue(RedditDownloader.validate("http://www.reddit.com/r/nsfw/", parent))

        self.assertTrue(RedditDownloader.validate("http://www.reddit.com/r/AutumnPorn/"))
        self.assertTrue(
            RedditDownloader.validate("http://www.reddit.com/r/AutumnPorn/top?sort=top&t=month")
        )
        self.assertFalse(RedditDownloader.validate("http://www.reddit.com/r/bestof/"))
        self.assertFalse(
            RedditDownloader.validate("http://www.reddit.com/r/dhkjregfhjregfjfdrejh/")
        )
        self.assertFalse(
            RedditDownloader.validate("http://www.notreddit.com/r/dhkjregfhjregfjfdrejh/")
        )


if __name__ == "__main__":
    unittest.main()
