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

import sys
import os.path
import unittest

from tests.TestDownloader import test_download_one_for

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from variety.MediaRssDownloader import MediaRssDownloader


class TestMediaRssDownloader(unittest.TestCase):
    def test_download_one(self):
        test_download_one_for(self, MediaRssDownloader(None, "http://backend.deviantart.com/rss.xml?q=boost%3Apopular+leaves&type=deviation"))

    def test_validate_deviantart(self):
        self.assertTrue(MediaRssDownloader.validate("http://backend.deviantart.com/rss.xml?q=boost%3Apopular+leaves&type=deviation"))

    def test_validate_non_media_rss(self):
        self.assertFalse(MediaRssDownloader.validate("http://www.dnevnik.bg/rss/?page=index"))

    def test_validate_non_rss(self):
        self.assertFalse(MediaRssDownloader.validate("http://google.com"))

if __name__ == '__main__':
    unittest.main()
