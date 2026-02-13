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
import unittest

from jumble.Jumble import Jumble

@unittest.skipIf(os.getenv("SKIP_DOWNLOADER_TESTS"), "Skipping downloader tests (SKIP_DOWNLOADER_TESTS is set)")
class TestGoodreadsSource(unittest.TestCase):
    def test_get_for_author(self):
        p = Jumble(["variety/plugins/builtin"])
        p.load()
        source = p.get_plugins(typename="GoodreadsSource")[0]
        q = source["plugin"].get_for_author("Вежинов")
        self.assertTrue(len(q) > 0)
        self.assertEqual("Goodreads", q[0]["sourceName"])
