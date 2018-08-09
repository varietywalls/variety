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
import shutil
import sys
import os.path
import unittest

from tests import setup_test_logging
from variety import Util

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

setup_test_logging()

from variety.Downloader import Downloader

def test_download_one_for(test_case, dl):
    dl.target_folder = '/tmp/variety/%s' % dl.__class__.__name__
    shutil.rmtree(dl.target_folder, ignore_errors=True)
    for _ in range(5):
        f = dl.download_one()
        if f and os.path.isfile(f) and Util.is_image(f, check_contents=True):
            return
    test_case.fail("Tried download_one 5 times, all failed")

class TestDownloader(unittest.TestCase):
    def test_convert_url(self):
        self.assertEqual("wallpapers_net_some_category_html",
            Downloader("", "", "", ".").convert_to_filename("http://wallpapers.net/some-category.html"))

if __name__ == '__main__':
    unittest.main()
