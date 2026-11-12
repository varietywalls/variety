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
import unittest
from unittest import mock

from tests.TestDownloader import get_plugin_downloader, test_download_one_for
from variety.plugins.builtin.downloaders.APODDownloader import APODDownloader, _strip_html


def _item(day, media_type="image", hdurl=True):
    return {
        "date": "2026-11-%02d" % day,
        "title": "Title %d" % day,
        "permalink": "https://science.nasa.gov/image-article/apod-%d/" % day,
        "media_type": media_type,
        "explanation": "<strong>Explanation:</strong> Text %d" % day,
        "credit": "Image Credit &amp; Copyright: <a href='#'>Someone</a>",
        "hdurl": "https://assets.science.nasa.gov/x/pic%%20%d.jpg?w=0&h=0" % day if hdurl else "",
    }


class TestAPODDownloaderOffline(unittest.TestCase):
    def setUp(self):
        self.dl = APODDownloader()
        self.dl.get_variety = lambda: None

    def test_fill_queue_keeps_latest_first_and_skips_non_images(self):
        latest = [_item(d) for d in (11, 10, 9, 8)] + [_item(7, media_type="video")]
        older = [_item(1), _item(2, hdurl=False)]
        with mock.patch(
            "variety.plugins.builtin.downloaders.APODDownloader.Util.fetch_json",
            side_effect=[latest, older],
        ) as fetch:
            queue = self.dl.fill_queue()
        self.assertIn("page=1&", fetch.call_args_list[0][0][0])
        self.assertEqual([x["date"][-2:] for x in queue[:3]], ["11", "10", "09"])
        self.assertEqual(sorted(x["date"][-2:] for x in queue[3:]), ["01", "08"])

    def test_fill_queue_survives_older_page_failure(self):
        with mock.patch(
            "variety.plugins.builtin.downloaders.APODDownloader.Util.fetch_json",
            side_effect=[[_item(11)], Exception("boom")],
        ):
            queue = self.dl.fill_queue()
        self.assertEqual(len(queue), 1)

    def test_download_queue_item_metadata_and_filename(self):
        with mock.patch.object(self.dl, "save_locally", return_value="/f") as save:
            self.assertEqual(self.dl.download_queue_item(_item(11)), "/f")
        args, kwargs = save.call_args
        self.assertEqual(args[0], "https://science.nasa.gov/image-article/apod-11/")
        self.assertEqual(kwargs["local_filename"], "2026-11-11_pic 11.jpg")
        self.assertEqual(
            kwargs["extra_metadata"],
            {"headline": "Title 11", "description": "Text 11", "author": "Someone"},
        )

    def test_strip_html(self):
        self.assertIsNone(_strip_html(None))
        self.assertEqual(_strip_html("NASA, ESA", r"^Credit:\s*"), "NASA, ESA")


@unittest.skipIf(
    os.getenv("SKIP_DOWNLOADER_TESTS"), "Skipping downloader tests (SKIP_DOWNLOADER_TESTS is set)"
)
class TestAPODDownloader(unittest.TestCase):
    def test_download_one(self):
        dl = get_plugin_downloader("APODDownloader")
        test_download_one_for(self, dl)


if __name__ == "__main__":
    unittest.main()
