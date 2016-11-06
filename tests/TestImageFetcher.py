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
import shutil
import sys
import os.path
import unittest

from variety import Util

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from variety.ImageFetcher import ImageFetcher


class TestImageFetcher(unittest.TestCase):
    def test_fetch(self):
        target_folder = '/tmp/variety/ImageFetcher'
        shutil.rmtree(target_folder, ignore_errors=True)
        os.makedirs(target_folder)
        for url in ["http://unsplash.com/photos/7EqQ1s3wIAI/download",]:
            f = ImageFetcher.fetch(url, target_folder, verbose=False)
            self.assertIsNotNone(f)
            self.assertTrue(os.path.isfile(f))
            self.assertTrue(Util.is_image(f, check_contents=False))
            self.assertTrue(Util.is_image(f, check_contents=True))
            self.assertNotEqual('download', f)

    def test_extract_from_cd(self):
        self.assertEqual("img.jpg", ImageFetcher.extract_filename_from_content_disposition("attachment; filename=img.jpg"))
        self.assertEqual("img.jpg", ImageFetcher.extract_filename_from_content_disposition("attachment; filename='img.jpg'"))
        self.assertEqual("img.jpg", ImageFetcher.extract_filename_from_content_disposition('attachment; filename="img.jpg"'))
        self.assertEqual(None, ImageFetcher.extract_filename_from_content_disposition('attachment; a=b'))

    def test_url_ok(self):
        self.assertFalse(ImageFetcher.url_ok("some garbage", False, ["flickr.com"]))
        self.assertFalse(ImageFetcher.url_ok("some garbage", True, ["flickr.com"]))
        self.assertFalse(ImageFetcher.url_ok("http://www.host.com/x/y/z", False, ["flickr.com"]))
        self.assertFalse(ImageFetcher.url_ok("http://cnn.com/x/y", True, ["flickr.com"]))
        self.assertFalse(ImageFetcher.url_ok("http://somehost.com/x/y", True, ["","flickr.com"]))
        self.assertTrue(ImageFetcher.url_ok("http://www.host.com/x/y/z.jpg", False, ["flickr.com"]))
        self.assertTrue(ImageFetcher.url_ok("https://www.flickr.com/a", True, ["flickr.com"]))

if __name__ == '__main__':
    unittest.main()
