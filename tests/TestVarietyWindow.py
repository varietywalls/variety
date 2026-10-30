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
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from variety.Util import Util
from variety.VarietyWindow import VarietyWindow


class TestVarietyWindow(unittest.TestCase):
    def test_replace_clock_filter_offsets(self):
        f = "-fill '#DDDDDD' -annotate 0x0+[%HOFFSET+100]+[%VOFFSET+150] '%H:%M' -pointsize 50 -annotate 0x0+[%HOFFSET+100]+[%VOFFSET+100] '%A, %B %d'"
        ff = VarietyWindow.replace_clock_filter_offsets(f, 200, 3)
        expected = "-fill '#DDDDDD' -annotate 0x0+300+153 '%H:%M' -pointsize 50 -annotate 0x0+300+103 '%A, %B %d'"
        self.assertEqual(expected, ff)

    DAY = 24 * 60 * 60

    def _make_purge_window(self, folder, **option_overrides):
        options = SimpleNamespace(
            quota_enabled=False, quota_size=1000, quota_age_enabled=False, quota_age_days=30
        )
        for k, v in option_overrides.items():
            setattr(options, k, v)

        win = mock.MagicMock()
        win.options = options
        win.real_download_folder = folder
        win.download_folder_size = None
        win.current = None
        # use the real implementations for the helpers under test
        for name in ("_list_downloaded_files", "_delete_downloaded_file"):
            setattr(win, name, getattr(VarietyWindow, name).__get__(win))
        return win

    def _make_image(self, folder, name, size, age_days):
        path = os.path.join(folder, name)
        with open(path, "wb") as f:
            f.write(b"0" * size)
        with open(path + ".metadata.json", "w") as f:
            f.write("{}")
        # ctime can't be set directly; point the listing at a fake ctime instead
        return path

    def test_purge_downloaded_by_age(self):
        with tempfile.TemporaryDirectory() as folder:
            old = self._make_image(folder, "old.jpg", 100, 40)
            new = self._make_image(folder, "new.jpg", 100, 1)
            current = self._make_image(folder, "current.jpg", 100, 50)

            win = self._make_purge_window(folder, quota_age_enabled=True, quota_age_days=30)
            win.current = current
            now = time.time()
            fake_listing = [
                (old, 100, now - 40 * self.DAY),
                (new, 100, now - 1 * self.DAY),
                (current, 100, now - 50 * self.DAY),
            ]
            win._list_downloaded_files = mock.Mock(return_value=fake_listing)

            VarietyWindow.purge_downloaded(win)

            self.assertFalse(os.path.exists(old))
            self.assertFalse(os.path.exists(old + ".metadata.json"))
            self.assertTrue(os.path.exists(new))
            self.assertTrue(os.path.exists(current))  # the current wallpaper is never deleted
            win.prepare_event.set.assert_called()

    def test_purge_downloaded_disabled_does_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            old = self._make_image(folder, "old.jpg", 100, 400)
            win = self._make_purge_window(folder)
            win._list_downloaded_files = mock.Mock(
                return_value=[(old, 100, time.time() - 400 * self.DAY)]
            )

            VarietyWindow.purge_downloaded(win)

            self.assertTrue(os.path.exists(old))

    def test_purge_downloaded_by_size_quota(self):
        with tempfile.TemporaryDirectory() as folder:
            mb = 1024 * 1024
            files = []
            now = time.time()
            for i in range(5):
                path = self._make_image(folder, "img%d.jpg" % i, 10, 0)
                files.append((path, 20 * mb, now - (5 - i) * self.DAY))  # img0 is the oldest

            win = self._make_purge_window(folder, quota_enabled=True, quota_size=90)
            win.download_folder_size = 100 * mb  # over 95% of the quota
            win._list_downloaded_files = mock.Mock(return_value=files)
            with mock.patch.object(Util, "get_folder_size", return_value=100 * mb):
                VarietyWindow.purge_downloaded(win)

            remaining = sorted(f for f in os.listdir(folder) if not f.endswith(".json"))
            # the oldest files go first, and purging stops once under 80% of the quota (72 MB)
            self.assertEqual(["img2.jpg", "img3.jpg", "img4.jpg"], remaining)
            self.assertEqual(60 * mb, win.download_folder_size)


if __name__ == "__main__":
    unittest.main()
