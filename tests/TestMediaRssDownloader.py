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

from data.plugins.downloaders.MediaRSSDownloader import MediaRSSDownloader
from data.plugins.downloaders.MediaRSSSource import MediaRSSSource
from tests.TestDownloader import test_download_one_for


class TestMediaRssDownloader(unittest.TestCase):
    def test_download_one(self):
        test_download_one_for(
            self,
            MediaRSSSource().create_downloader(
                "http://backend.deviantart.com/rss.xml?q=boost%3Apopular+leaves&type=deviation"
            ),
        )

    def test_validate_deviantart(self):
        self.assertTrue(
            MediaRSSDownloader.validate(
                "http://backend.deviantart.com/rss.xml?q=boost%3Apopular+leaves&type=deviation"
            )
        )

    def test_validate_non_media_rss(self):
        self.assertFalse(MediaRSSDownloader.validate("http://www.dnevnik.bg/rss/?page=index"))

    def test_validate_non_rss(self):
        self.assertFalse(MediaRSSDownloader.validate("http://google.com"))


if __name__ == "__main__":
    unittest.main()
