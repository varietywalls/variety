#!/usr/bin/python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2012 Peter Levi <peterlevi@peterlevi.com>
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
import urllib2
import json

import logging

logger = logging.getLogger('variety')

from variety import Downloader

class DesktopprDownloader(Downloader.Downloader):
    def __init__(self, download_folder):
        super(DesktopprDownloader, self).__init__(
            "Desktoppr.co", "https://api.desktoppr.co/1/wallpapers/random", download_folder)
        self.target_folder = os.path.join(download_folder, "Desktoppr")

    def download_one(self):
        logger.info("Downloading a random image from desktoppr.co")

        content = urllib2.urlopen(self.location).read()
        response = json.loads(content)
        image_url = response["response"]["image"]["url"]
        self.save_locally("http://www.desktoppr.co", image_url)
