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
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from tests.TestDownloader import test_download_one_for
from variety.plugins.builtin.downloaders.WallhavenSource import WallhavenSource
from variety.Util import Util


class TestWallhavenDownloader(unittest.TestCase):
    def test_download_one(self):
        source = WallhavenSource()
        mock = MagicMock()
        mock.options.wallhaven_api_key = ""
        source.set_variety(mock)
        test_download_one_for(self, source.create_downloader("landscape"))

    def test_legacy_fallback_download_one(self):
        source = WallhavenSource()
        mock = MagicMock()
        mock.options.wallhaven_api_key = ""
        source.set_variety(mock)

        with tempfile.TemporaryDirectory() as tmpdir:
            dl = source.create_downloader("https://wallhaven.cc/user/lewdpatriot/favorites/935888")
            dl.update_download_folder(tmpdir)
            for _ in range(5):
                f = dl.download_one()
                if f and os.path.isfile(f) and Util.is_image(f, check_contents=True):
                    return
            self.fail("Tried download_one 5 times, all failed")

    def test_fill_queue(self):
        source = WallhavenSource()
        mock = MagicMock()
        mock.options.wallhaven_api_key = ""
        source.set_variety(mock)
        dl = source.create_downloader("nature")
        queue = dl.fill_queue()
        self.assertTrue(len(queue) > 0)


if __name__ == "__main__":
    unittest.main()
