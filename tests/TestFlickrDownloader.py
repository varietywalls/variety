#!/usr/bin/python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2012 Peter Levi <peterlevi@peterlevi.com>
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

import sys
import os.path
import unittest
from variety.FlickrDownloader import FlickrDownloader

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

class TestFlickrDownloader(unittest.TestCase):
    def test_obtain_userid_ok(self):
        self.assertEqual((True, "ok", "34388055@N08"),
            FlickrDownloader.obtain_userid("http://www.flickr.com/photos/camillelacroix/"))

    def test_obtain_userid_fail(self):
        self.assertEqual((False, "User not found", None),
            FlickrDownloader.obtain_userid("http://www.flickr.com/photos/bad_username_here_xxx/"))

    def test_obtain_groupid_ok(self):
        self.assertEqual((True, "ok", "40961104@N00"),
            FlickrDownloader.obtain_groupid("http://www.flickr.com/groups/wallpapers/"))

    def test_obtain_groupid_fail(self):
        self.assertEqual((False, "Group not found", None),
            FlickrDownloader.obtain_groupid("http://www.flickr.com/groups/bad_groupname_here_xxx/"))

if __name__ == '__main__':
    unittest.main()
