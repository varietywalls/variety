#!/usr/bin/python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Peter Levi <peterlevi@peterlevi.com>
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
from variety.Util import Util

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

class TestUtil(unittest.TestCase):
    def test_get_local_name(self):
        self.assertEqual("img.jpg", Util.get_local_name("http://example.com/a/img.jpg?a=b"))
        self.assertEqual("img.jpg", Util.get_local_name("http://example.com/a/img.jpg#x"))
        self.assertEqual("img.jpg", Util.get_local_name("http://example.com/a/img.jpg?a=b#x"))
        self.assertEqual("im g.jpg", Util.get_local_name("http://example.com/a/im%20g.jpg?a=b#x"))
        self.assertEqual("im_g.jpg", Util.get_local_name("http://example.com/a/im%22g.jpg?a=b#x"))

    def test_split(self):
        self.assertEqual(['a','b','c','d','e'], Util.split("a\nb,c ,,d\n   e"))

    def test_metadata(self):
        self.assertTrue(os.path.exists('test.jpg'))
        info = {"sourceName": 'a', "sourceURL": 'b', "sourceLocation": 'c', "imageURL": 'd'}
        Util.write_metadata('test.jpg', info)
        self.assertEqual(info, Util.read_metadata('test.jpg'))
        Util.write_metadata('test.svg', info)
        self.assertEqual(info, Util.read_metadata('test.svg'))

    def test_find_unique_name(self):
        self.assertEquals('/etc/fstab_1', Util.find_unique_name('/etc/fstab'))
        self.assertEquals('/etc/bash_1.bashrc', Util.find_unique_name('/etc/bash.bashrc'))

if __name__ == '__main__':
    unittest.main()
