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
import random
import logging

random.seed()
logger = logging.getLogger('variety')

class Util:
    @staticmethod
    def get_local_name(url):
        filename = url[url.rindex('/') + 1:]
        index = filename.find('?')
        if index > 0:
            filename = filename[:index]
        index = filename.find('#')
        if index > 0:
            filename = filename[:index]
        return filename

    @staticmethod
    def split(s, seps=(',', ' ')):
        result = s.split()
        for sep in seps:
            result = [x.strip() for y in result for x in y.split(sep) if x.strip()]
        return result

    @staticmethod
    def makedirs(path):
        try:
            os.makedirs(path)
        except OSError:
            pass

    @staticmethod
    def is_image(filename):
        return filename.lower().endswith(('.jpg', '.jpeg', '.gif', '.png', '.tiff'))

    @staticmethod
    def list_files(files=(), folders=(), filter_func=(lambda f: True), max_files=10000, randomize=False):
        count = 0
        for filepath in files:
            if filter_func(filepath) and os.access(filepath, os.R_OK):
                count += 1
                yield filepath

        folders = list(folders)
        if randomize:
            random.shuffle(folders)

        for folder in folders:
            if os.path.isdir(folder):
                try:
                    for root, subFolders, files in os.walk(folder):
                        for filename in files:
                            if filter_func(filename):
                                count += 1
                                if count > max_files:
                                    logger.info("More than %d files in the folders, stop listing" % max_files)
                                    return
                                yield os.path.join(root, filename)
                except Exception:
                    logger.exception("Cold not walk folder " + folder)
