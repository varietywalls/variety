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
import threading
import time
import pyexiv2

VARIETY_INFO = "Downloaded by Variety wallpaper changer, https://launchpad.net/variety"

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
        return filename.lower().endswith(('.jpg', '.jpeg', '.gif', '.png', '.tiff', '.svg'))

    @staticmethod
    def list_files(files=(), folders=(), filter_func=(lambda f: True), max_files=10000, randomize=True):
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
                        if randomize:
                            random.shuffle(files)
                            random.shuffle(subFolders)
                        for filename in files:
                            if filter_func(filename):
                                count += 1
                                if count > max_files:
                                    logger.info("More than %d files in the folders, stop listing" % max_files)
                                    return
                                yield os.path.join(root, filename)
                except Exception:
                    logger.exception("Cold not walk folder " + folder)

    @staticmethod
    def start_force_exit_thread(delay):
        def force_exit():
            time.sleep(delay)
            print "Exiting takes too long. Calling os.kill."
            os.kill(os.getpid(), 9)
        force_exit_thread = threading.Thread(target=force_exit)
        force_exit_thread.daemon = True
        force_exit_thread.start()

    @staticmethod
    def write_metadata(filename, source, url):
        try:
            pyexiv2.xmp.register_namespace('https://launchpad.net/variety/', 'variety')
        except KeyError:
            pass

        try:
            m = pyexiv2.ImageMetadata(filename)
            m.read()
            m['Xmp.variety.info'] = VARIETY_INFO
            m['Xmp.variety.sourceName'] = source
            m['Xmp.variety.sourceURL'] = url
            m.write()
            return True
        except Exception:
            # could not write metadata inside file, use txt instead
            try:
                with open(filename + ".txt", 'w') as f:
                    f.write("INFO:\n" + source + "\n" + url +"\n" + VARIETY_INFO)
            except Exception:
                logger.exception("Could not write url metadata for file " + filename)
            return False

    @staticmethod
    def read_metadata(filename):
        try:
            pyexiv2.xmp.register_namespace('https://launchpad.net/variety/', 'variety')
        except KeyError:
            pass

        try:
            m = pyexiv2.ImageMetadata(filename)
            m.read()
            source = m['Xmp.variety.sourceName'].value
            url = m['Xmp.variety.sourceURL'].value
            return source, url
        except Exception, e:
            # could not read metadata inside file, use txt instead
            try:
                with open(filename + ".txt") as f:
                    lines = list(f)
                    if len(lines) >= 3 and lines[0].strip() == "INFO:":
                        source = lines[1].strip().replace("Downloaded from ", "") # TODO remove later on
                        url = lines[2].strip()
                        return source, url
                    else:
                        return None, None
            except Exception:
                return None, None



