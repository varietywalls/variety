#!/usr/bin/python2
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

from variety.VarietyWindow import VarietyWindow


class TestVarietyWindow(unittest.TestCase):
    def test_replace_clock_filter_offsets(self):
        f = "-fill '#DDDDDD' -annotate 0x0+[%HOFFSET+100]+[%VOFFSET+150] '%H:%M' -pointsize 50 -annotate 0x0+[%HOFFSET+100]+[%VOFFSET+100] '%A, %B %d'"
        ff = VarietyWindow.replace_clock_filter_offsets(f, 200, 3)
        expected = "-fill '#DDDDDD' -annotate 0x0+300+153 '%H:%M' -pointsize 50 -annotate 0x0+300+103 '%A, %B %d'"
        self.assertEqual(expected, ff)

if __name__ == '__main__':
    unittest.main()
