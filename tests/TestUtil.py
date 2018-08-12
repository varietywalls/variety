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

import sys
import os.path
import unittest
import time

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from variety.Util import Util, debounce, throttle, cache


class TestUtil(unittest.TestCase):
    def test_sanitize_filename(self):
        self.assertEqual("i_m____g_.jpg", Util.sanitize_filename("i?m?*%^g_.jpg"))

    def test_get_local_name(self):
        self.assertEqual("img.jpg", Util.get_local_name("http://example.com/a/img?a=b"))
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
            'sourceURL': 'b',
            'imageURL': 'd',
            'sourceName': 'a',
            'sourceLocation': 'c',
            'sourceType': 'flickr',
            'author': 'автор',
            'authorURL': 'url',
            'keywords': ['дума1', 'дума2'],
            'headline': 'проба1 проба1',
            'description': 'проба2 проба2',
            'sfwRating': 50,
            'extraData': {'key1': 'val1', 'key2': 'val2'}
        }
        self.assertEqual(info, Util.read_metadata('test.jpg'))
        self.assertTrue(Util.write_metadata('test.jpg', info))
        self.assertEqual(info, Util.read_metadata('test.jpg'))

        self.assertTrue(os.path.exists('test.svg'))
        self.assertEqual(info, Util.read_metadata('test.svg'))
        Util.write_metadata('test.svg', info)
        self.assertEqual(info, Util.read_metadata('test.svg'))

    def test_read_write_rating(self):
        self.assertTrue(os.path.exists('test.jpg'))
        self.assertEqual(None, Util.get_rating('test.jpg'))

        Util.set_rating('test.jpg', None)
        self.assertEqual(None, Util.get_rating('test.jpg'))

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
        self.assertEqual('/etc/fstab_1', Util.find_unique_name('/etc/fstab'))
        self.assertEqual('/etc/bash_1.bashrc', Util.find_unique_name('/etc/bash.bashrc'))

    def test_folderpath(self):
        self.assertEqual("/", Util.folderpath("/"))
        self.assertEqual("/a/b/c/", Util.folderpath("/a/b/c"))

    def test_gtk_to_fcmatch_font(self):
        self.assertEqual(
            ("Bitstream Charter:Bold:Italic:10", '10'), Util.gtk_to_fcmatch_font("Bitstream Charter Bold Italic 10"))

    def test_file_in(self):
        self.assertTrue(Util.file_in("/a/b/a.txt", "/a/"))
        self.assertTrue(Util.file_in("/a/b/a.txt", "/a/b/"))
        self.assertFalse(Util.file_in("/a/b/a.txt", "/c/"))

    def test_same_file_paths(self):
        self.assertTrue(Util.same_file_paths("/a/../b/c", "/b/c"))
        self.assertFalse(Util.same_file_paths("/a/../b/c", "/a/./b/c"))

    def test_compare_versions(self):
        self.assertEqual(-1, Util.compare_versions("0.4.10", "0.4.11"))
        self.assertEqual(-1, Util.compare_versions("0.4.10", "0.5"))
        self.assertEqual(-1, Util.compare_versions("0.4.10", "1"))
        self.assertEqual(0, Util.compare_versions("0.4.10", "0.4.10"))
        self.assertEqual(1, Util.compare_versions("0.4.10", "0.4.8"))
        self.assertEqual(1, Util.compare_versions("0.4.10", "0.4"))
        self.assertEqual(1, Util.compare_versions("0.4.10", "0"))

    def test_md5(self):
        self.assertEqual("098f6bcd4621d373cade4e832627b4f6", Util.md5("test"))

    def test_md5file(self):
        self.assertEqual("633de9e37fd782d79b59c626695ac2ef", Util.md5file("test.jpg"))

    def test_collapseuser(self):
        self.assertEqual("~/.config/variety", Util.collapseuser("/home/peter/.config/variety"))
        self.assertEqual("/home/peteraaa/.config/variety", Util.collapseuser("/home/peteraaa/.config/variety"))
        self.assertEqual("/media/.config/variety", Util.collapseuser("/media/.config/variety"))

    def test_random_hash(self):
        s = set(Util.random_hash() for i in range(100))
        self.assertEqual(100, len(s))
        for x in s:
            self.assertEqual(32, len(x))

    def test_get_file_icon_name(self):
        self.assertEqual("folder", Util.get_file_icon_name("/xxx/yyy/zzz")) # nonexistent
        self.assertEqual("user-home", Util.get_file_icon_name("~"))
        self.assertEqual("folder-pictures", Util.get_file_icon_name("~/Pictures"))

    def test_get_xdg_pictures_folder(self):
        self.assertEqual(os.path.expanduser('~/Pictures'), Util.get_xdg_pictures_folder())

    def test_safe_map(self):
        def f(i):
            if i <= 10: raise Exception
            return i
        self.assertEqual([20,30], list(Util.safe_map(f, [1,5,20,10,30,4])))

    def test_fetch(self):
        resp = Util.fetch("//google.com")
        self.assertTrue(len(resp) > 0)

    def test_get_size(self):
        self.assertEqual((32, 32), Util.get_size('test.jpg'))
        self.assertRaises(Exception, lambda: Util.get_size('fake_image.jpg'))

    def test_is_image(self):
        self.assertTrue(Util.is_image('test.jpg'))
        self.assertTrue(Util.is_image('test.jpg', check_contents=True))
        self.assertTrue(Util.is_image('fake_image.jpg'))
        self.assertFalse(Util.is_image('fake_image.jpg', check_contents=True))

    def test_is_animated_gif(self):
        self.assertFalse(Util.is_animated_gif('test.jpg'))
        self.assertTrue(Util.is_animated_gif('animated.gif'))
        self.assertFalse(Util.is_animated_gif('not-animated.gif'))

    def test_is_dead_or_not_image(self):
        self.assertTrue(Util.is_dead_or_not_image(None))
        self.assertTrue(Util.is_dead_or_not_image('not a URL'))
        self.assertTrue(Util.is_dead_or_not_image('http://www.google.com/'))
        self.assertTrue(Util.is_dead_or_not_image('http://vrty.org/'))
        self.assertTrue(Util.is_dead_or_not_image('http://www.google.com/dejkjdrelkjflkrejfjre'))
        self.assertFalse(Util.is_dead_or_not_image('http://upload.wikimedia.org/wikipedia/commons/5/53/Wikipedia-logo-en-big.png'))
        self.assertFalse(Util.is_dead_or_not_image('https://farm8.staticflickr.com/7133/7527967878_85fea93129_o.jpg'))
        self.assertFalse(Util.is_dead_or_not_image('http://interfacelift.com/wallpaper/D98ef829/00899_rustedbolt_2560x1600.jpg'))
        self.assertTrue(Util.is_dead_or_not_image('http://wallpapers.wallbase.cc/rozne/wallpaper-1227671.jpg'))
        self.assertTrue(Util.is_dead_or_not_image('http://ns223506.ovh.net/rozne/a1b2/wallpaper-1996019.png'))

    def test_guess_image_url(self):
        self.assertEqual('https://farm5.staticflickr.com/4032/4558166441_4e34855b39_o.jpg',
                          Util.guess_image_url({'sourceURL': 'https://www.flickr.com/photos/83646108@N00/4558166441'}))

        self.assertEqual('https://farm5.staticflickr.com/4077/4768189432_24275ea76b_b.jpg',
                          Util.guess_image_url({'sourceURL': 'http://www.flickr.com/photos/52821721@N00/4768189432'}))

        self.assertEqual('http://fc04.deviantart.net/fs71/i/2011/319/4/f/scarlet_leaf_wallpaper_by_venomxbaby-d4gc238.jpg',
                          Util.guess_image_url({'sourceURL': 'http://fc04.deviantart.net/fs71/i/2011/319/4/f/scarlet_leaf_wallpaper_by_venomxbaby-d4gc238.jpg'}))

    def test_guess_source_type(self):
        self.assertEqual(None, Util.guess_source_type({}))
        self.assertEqual('mediarss', Util.guess_source_type({'sourceName': 'host.com', 'sourceLocation': 'http://host.com/rss'}))
        self.assertEqual('mediarss', Util.guess_source_type({'sourceName': 'camelid.deviantart.com', 'sourceLocation': 'http://backend.deviantart.com/rss.xml?type=deviation&q=by%3ACamelid+sort%3Atime+meta%3Aall'}))

    def test_debounce(self):
        """ Test that the increment function is being debounced.
        The counter should only be incremented once 10 seconds after the last call to the function """
        count = [0]

        @debounce(0.6)
        def increment():
            count[0] += 1

        self.assertTrue(count[0] == 0)
        increment()
        increment()
        time.sleep(0.4)
        self.assertTrue(count[0]== 0)
        increment()
        increment()
        increment()
        increment()
        self.assertTrue(count[0] == 0)
        time.sleep(0.6)
        self.assertTrue(count[0] == 1)


    def test_throttle_no_trailing(self):
        count = [0]

        @throttle(seconds=0.3)
        def increment():
            count[0] += 1

        self.assertTrue(count[0] == 0)
        increment()
        self.assertTrue(count[0] == 1)
        increment()
        self.assertTrue(count[0] == 1)
        time.sleep(0.2)
        increment()
        self.assertTrue(count[0] == 1)
        time.sleep(0.2)
        increment()
        self.assertTrue(count[0] == 2)
        increment()
        self.assertTrue(count[0] == 2)
        time.sleep(0.31)
        self.assertTrue(count[0] == 2)

    def test_throttle_with_trailing(self):
        count = [0]

        @throttle(seconds=0.3, trailing_call=True)
        def increment():
            count[0] += 1

        self.assertTrue(count[0] == 0)
        increment()
        self.assertTrue(count[0] == 1)
        increment()
        self.assertTrue(count[0] == 1)
        time.sleep(0.2)
        increment()
        self.assertTrue(count[0] == 1)
        time.sleep(0.2)
        increment()
        self.assertTrue(count[0] == 2)
        increment()
        self.assertTrue(count[0] == 2)
        time.sleep(0.31)
        self.assertTrue(count[0] == 3)

    def test_cache(self):
        @cache(ttl_seconds=10)
        def fib(n):
            return 1 if n <= 1 else fib(n - 1) + fib(n - 2)

        self.assertEqual(573147844013817084101, fib(100))

if __name__ == '__main__':
    unittest.main()
