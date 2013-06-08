#!/usr/bin/python
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
from jumble.Jumble import Jumble

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

class TestQuotationsPageSource(unittest.TestCase):
    def test_get_random(self):
        p = Jumble(["../plugins"])
        p.load()
        source = p.get_plugins(typename="QuotationsPageSource")[0]
        q = source["plugin"].get_random()
        self.assertTrue(len(q) > 0)
        self.assertEqual("TheQuotationsPage.com", q[0]["sourceName"])

    def test_get_for_author(self):
        p = Jumble(["../plugins"])
        p.load()
        source = p.get_plugins(typename="QuotationsPageSource")[0]
        q = source["plugin"].get_for_author("einstein")
        self.assertTrue(len(q) > 0)
        self.assertEqual("TheQuotationsPage.com", q[0]["sourceName"])
        self.assertEqual("Albert Einstein", q[0]["author"])

    def test_get_for_keyword(self):
        p = Jumble(["../plugins"])
        p.load()
        source = p.get_plugins(typename="QuotationsPageSource")[0]
        q = source["plugin"].get_for_keyword("funny")
        self.assertTrue(len(q) > 0)
        self.assertEqual("TheQuotationsPage.com", q[0]["sourceName"])
        self.assertTrue(q[0]["quote"].lower().find('funny') >= 0)
