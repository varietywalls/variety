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

import os
import string
import urllib2
import re

import logging

logger = logging.getLogger('variety')

class Downloader(object):
    def __init__(self, parent, name, location):
        self.parent = parent
        self.name = name
        self.location = location

    def update_download_folder(self):
        self.target_folder = os.path.join(self.parent.options.download_folder, self.convert_to_filename(self.location))

    def convert_to_filename(self, url):
        url = re.sub(r"http://", "", url)
        valid_chars = "_%s%s" % (string.ascii_letters, string.digits)
        return ''.join(c if c in valid_chars else '_' for c in url)

    def get_local_filename(self, url):
        filename = url[url.rindex('/') + 1:]
        return os.path.join(self.target_folder, filename)

    def save_locally(self, origin_url, image_url):
        if origin_url in self.parent.banned:
            logger.info("URL " + origin_url + " is banned, skip downloading")
            return None

        try:
            os.makedirs(self.target_folder)
        except Exception:
            pass

        local_filename = self.get_local_filename(image_url)
        logger.info("Name: " + local_filename)

        if os.path.exists(local_filename):
            logger.info("File already exists, skip downloading")
            return None

        u = urllib2.urlopen(image_url)
        data = u.read()
        localFile = open(local_filename, 'wb')
        localFile.write(data)
        localFile.close()

        localFile = open(local_filename + ".txt", 'w')
        localFile.write("INFO:\n" + self.name + "\n" + origin_url)
        localFile.close()

        logger.info("Download complete")
        return local_filename
