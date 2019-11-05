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
from variety.FlickrDownloader import FlickrDownloader


class TestFlickrDownloader(unittest.TestCase):
    def test_download_one(self):
        test_download_one_for(
            self,
            FlickrDownloader(None, "user:www.flickr.com/photos/peter-levi/;user_id:93647178@N00;"),
        )

    def test_obtain_userid_ok(self):
        self.assertEqual(
            (True, "ok", "34388055@N08"),
            FlickrDownloader.obtain_userid("http://www.flickr.com/photos/camillelacroix/"),
        )

    def test_obtain_userid_fail(self):
        self.assertEqual(
            (False, "User not found", None),
            FlickrDownloader.obtain_userid("http://www.flickr.com/photos/bad_username_here_xxx/"),
        )

    def test_obtain_groupid_ok(self):
        self.assertEqual(
            (True, "ok", "40961104@N00"),
            FlickrDownloader.obtain_groupid("http://www.flickr.com/groups/wallpapers/"),
        )

    def test_obtain_groupid_fail(self):
        self.assertEqual(
            (False, "Group not found", None),
            FlickrDownloader.obtain_groupid("http://www.flickr.com/groups/bad_groupname_here_xxx/"),
        )

    def test_get_photo_id(self):
        self.assertEqual(
            "7527967456",
            FlickrDownloader.get_photo_id("https://www.flickr.com/photos/peter-levi/7527967456/"),
        )
        self.assertEqual(
            "7527967456",
            FlickrDownloader.get_photo_id("https://www.flickr.com/photos/peter-levi/7527967456"),
        )

    def test_get_image_url(self):
        self.assertEqual(
            "https://live.staticflickr.com/8426/7527967456_41f8ae5caf_k.jpg",
            FlickrDownloader.get_image_url("https://www.flickr.com/photos/peter-levi/7527967456/"),
        )

    def test_get_extra_metadata(self):
        expected = {
            "headline": "IMG_1924",
            "keywords": ["greece", "greek", "islands"],
            "description": "",
            "authorURL": "https://www.flickr.com/photos/93647178@N00",
            "author": "Peter Levi",
        }
        self.assertEqual(
            expected,
            FlickrDownloader.get_extra_metadata(
                "https://www.flickr.com/photos/peter-levi/7527967456/"
            ),
        )


if __name__ == "__main__":
    unittest.main()
