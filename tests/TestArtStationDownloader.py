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
from variety.plugins.builtin.downloaders.ArtStationSource import ArtStationSource


class TestArtStationDownloader(unittest.TestCase):
    def test_download_one(self):
        test_download_one_for(
            self,
            ArtStationSource().create_downloader("https://www.artstation.com/anubis1982918.rss"),
        )

    def test_validate(self):
        source = ArtStationSource()
        self.assertEqual(
            ("https://www.artstation.com/anubis1982918.rss", None),
            source.validate("https://www.artstation.com/anubis1982918.rss"),
        )
        self.assertEqual(
            ("https://www.artstation.com/anubis1982918.rss", None),
            source.validate("https://www.artstation.com/anubis1982918"),
        )
        self.assertEqual(
            ("https://www.artstation.com/anubis1982918.rss", None),
            source.validate("https://artstation.com/anubis1982918"),
        )
        self.assertEqual(
            ("https://www.artstation.com/anubis1982918.rss", None),
            source.validate("http://artstation.com/anubis1982918"),
        )
        self.assertEqual(
            ("https://www.artstation.com/anubis1982918.rss", None), source.validate("anubis1982918")
        )
        self.assertIsNotNone(source.validate("http://cnn.com")[1])


if __name__ == "__main__":
    unittest.main()
