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
from TestDownloader import test_download_one_for

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from variety.PanoramioDownloader import PanoramioDownloader


class TestPanoramioDownloader(unittest.TestCase):
    def test_download_one(self):
        test_download_one_for(self, PanoramioDownloader(
            None, '{"zoom":1,"center":{"lat":0,"lng":20},"minx":-180,"miny":-83.82994542398042,"maxx":180,"maxy":83.82994542398042}'))

if __name__ == '__main__':
    unittest.main()
