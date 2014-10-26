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
from variety.Util import Util

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

class TestUtil(unittest.TestCase):
    def test_get_local_name(self):
        self.assertEqual("img.jpg", Util.get_local_name("http://example.com/a/img.jpg?a=b"))
        self.assertEqual("img.jpg", Util.get_local_name("http://example.com/a/img.jpg#x"))
        self.assertEqual("img.jpg", Util.get_local_name("http://example.com/a/img.jpg?a=b#x"))
        self.assertEqual("im g.jpg", Util.get_local_name("http://example.com/a/im%20g.jpg?a=b#x"))
        self.assertEqual("im_g.jpg", Util.get_local_name("http://example.com/a/im%22g.jpg?a=b#x"))

        self.assertTrue(len(Util.get_local_name("a" * 1000 + ".jpg")) < 255)

    def test_split(self):
        self.assertEqual(['a', 'b', 'c', 'd', 'e'], Util.split("a\nb,c ,,d\n   e"))

    def test_metadata(self):
        self.assertTrue(os.path.exists('test.jpg'))
        info = {
            'sourceURL': u'b',
            'imageURL': u'd',
            'sourceName': u'a',
            'sourceLocation': u'c',
            'sourceType': u'flickr',
            'author': u'автор',
            'authorURL': u'url',
            'keywords': [u'дума1', u'дума2'],
            'headline': u'проба1',
            'description': u'проба2',
            'sfwRating': 50,
        }
        self.assertTrue(Util.write_metadata('test.jpg', info))
        self.assertEqual(info, Util.read_metadata('test.jpg'))

        self.assertTrue(os.path.exists('test.svg'))
        Util.write_metadata('test.svg', info)
        self.assertEqual(info, Util.read_metadata('test.svg'))

    def test_read_write_rating(self):
        self.assertTrue(os.path.exists('test.jpg'))
        Util.set_rating('test.jpg', 4)
        self.assertEqual(4, Util.get_rating('test.jpg'))
        Util.set_rating('test.jpg', -1)
        self.assertEqual(-1, Util.get_rating('test.jpg'))
        Util.set_rating('test.jpg', 0)
        self.assertEqual(0, Util.get_rating('test.jpg'))
        Util.set_rating('test.jpg', None)
        self.assertEqual(None, Util.get_rating('test.jpg'))

        try:
            Util.set_rating('test.jpg', -10)
            self.assertTrue(False, "Exception expected")
        except ValueError:
            pass #OK

    def test_find_unique_name(self):
        self.assertEquals('/etc/fstab_1', Util.find_unique_name('/etc/fstab'))
        self.assertEquals('/etc/bash_1.bashrc', Util.find_unique_name('/etc/bash.bashrc'))

    def test_folderpath(self):
        self.assertEquals("/", Util.folderpath("/"))
        self.assertEquals("/a/b/c/", Util.folderpath("/a/b/c"))

    def test_gtk_to_fcmatch_font(self):
        self.assertEquals(
            ("Bitstream Charter:Bold:Italic:10", '10'), Util.gtk_to_fcmatch_font("Bitstream Charter Bold Italic 10"))

    def test_file_in(self):
        self.assertTrue(Util.file_in("/a/b/a.txt", "/a/"))
        self.assertTrue(Util.file_in("/a/b/a.txt", "/a/b/"))
        self.assertFalse(Util.file_in("/a/b/a.txt", "/c/"))

    def test_same_file_paths(self):
        self.assertTrue(Util.same_file_paths("/a/../b/c", "/b/c"))
        self.assertFalse(Util.same_file_paths("/a/../b/c", "/a/./b/c"))

    def test_compare_versions(self):
        self.assertEquals(-1, Util.compare_versions("0.4.10", "0.4.11"))
        self.assertEquals(-1, Util.compare_versions("0.4.10", "0.5"))
        self.assertEquals(-1, Util.compare_versions("0.4.10", "1"))
        self.assertEquals(0, Util.compare_versions("0.4.10", "0.4.10"))
        self.assertEquals(1, Util.compare_versions("0.4.10", "0.4.8"))
        self.assertEquals(1, Util.compare_versions("0.4.10", "0.4"))
        self.assertEquals(1, Util.compare_versions("0.4.10", "0"))

    def test_md5(self):
        self.assertEquals("098f6bcd4621d373cade4e832627b4f6", Util.md5("test"))

    def test_md5file(self):
        self.assertEquals("09e0399cd580cdae81102e676802e3cb", Util.md5file("test.jpg"))

    def test_collapseuser(self):
        self.assertEquals("~/.config/variety", Util.collapseuser("/home/peter/.config/variety"))
        self.assertEquals("/home/peteraaa/.config/variety", Util.collapseuser("/home/peteraaa/.config/variety"))
        self.assertEquals("/media/.config/variety", Util.collapseuser("/media/.config/variety"))

    def test_random_hash(self):
        s = set(Util.random_hash() for i in xrange(100))
        self.assertEquals(100, len(s))
        for x in s:
            self.assertEquals(32, len(x))

    def test_get_file_icon_name(self):
        self.assertEquals("folder", Util.get_file_icon_name("/xxx/yyy/zzz")) # nonexistent
        self.assertEquals("user-home", Util.get_file_icon_name("~"))
        self.assertEquals("folder-pictures", Util.get_file_icon_name("~/Pictures"))

    def test_get_xdg_pictures_folder(self):
        self.assertEquals(os.path.expanduser('~/Pictures'), Util.get_xdg_pictures_folder())

    def test_safe_map(self):
        def f(i):
            if i <= 10: raise Exception
            return i
        self.assertEquals([20,30], list(Util.safe_map(f, [1,5,20,10,30,4])))

    def test_urlopen(self):
        resp = Util.urlopen("//google.com")
        self.assertTrue(len(resp.read()) > 0)


if __name__ == '__main__':
    unittest.main()
