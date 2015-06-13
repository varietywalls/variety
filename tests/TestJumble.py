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

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from jumble.Jumble import Jumble
from jumble.IPlugin import IPlugin
from variety.plugins.IQuoteSource import IQuoteSource


class P1(IPlugin):
    pass

class P2(IQuoteSource):
    pass


class TestJumble(unittest.TestCase):
    def test_load(self):
        p = Jumble(["../data/plugins"])
        p.load()
        self.assertEqual(4, len(p.get_plugins()))
        self.assertEqual(4, len(p.get_plugins(IPlugin)))
        self.assertEqual(1, len(p.get_plugins(name="Goodreads")))
