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
import random
import json

import logging

logger = logging.getLogger('variety')

random.seed()

WN_HOST = "http://wallpapers.net"

class DesktopprDownloader():
    def __init__(self, download_folder):
        self.target_folder = os.path.join(download_folder, "Desktoppr")

    def download_one(self):
        logger.info("Downloading a random image from desktoppr.co")

        random_url = "https://api.desktoppr.co/1/wallpapers/random"
        content = urllib2.urlopen(random_url).read()
        response = json.loads(content)
        url = response["response"]["image"]["url"]
        self.save_locally("http://www.desktoppr.co", url)

    def save_locally(self, wallpaper_url, src_url):
        name = src_url[src_url.rindex('/') + 1:]
        logger.info("Name: " + name)

        try:
            os.makedirs(self.target_folder)
        except Exception:
            pass

        local_filename = os.path.join(self.target_folder, name)
        if os.path.exists(local_filename):
            logger.info("File already exists, skip downloading")
            return

        u = urllib2.urlopen(src_url)
        data = u.read()
        localFile = open(local_filename, 'wb')
        localFile.write(data)
        localFile.close()

        localFile = open(local_filename + ".txt", 'w')
        localFile.write("INFO:\nDownloaded from Desktoppr.co\n" + wallpaper_url)
        localFile.close()

        logger.info("Download complete")
