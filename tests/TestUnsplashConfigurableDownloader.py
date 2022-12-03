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
from variety.plugins.builtin.downloaders.UnsplashConfigurableSource import (
    UnsplashConfigurableSource,
)


class TestUnsplashConfigurableDownloader(unittest.TestCase):
    def _source(self):
        parent = AttrDict()
        parent.size_ok = lambda x, y: True
        source = UnsplashConfigurableSource()
        source.set_variety(parent)
        return source

    def test_download_one(self):
        test_download_one_for(self, self._source().create_downloader("landscape"))

    def test_validate(self):
        source = self._source()
        self.assertIsNone(source.validate("nature")[1])
        self.assertIsNone(source.validate("https://unsplash.com/s/photos/landscape")[1])
        self.assertIsNone(source.validate("https://unsplash.com/@pawel_czerwinski")[1])
        self.assertIsNone(
            source.validate("https://unsplash.com/collections/3694365/gradient-nation")[1]
        )

    def test_fill_queue(self):
        dl = self._source().create_downloader("nature")
        queue = dl.fill_queue()
        self.assertTrue(len(queue) > 0)


if __name__ == "__main__":
    unittest.main()
