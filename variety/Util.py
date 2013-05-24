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
import bs4
import hashlib
import json
import re
import os
import random
import logging
import string
import threading
import time
import pyexiv2
import urllib
import urllib2
from DominantColors import DominantColors
from gi.repository import Gdk, Pango, GdkPixbuf
import inspect
import subprocess

VARIETY_INFO = "Downloaded by Variety wallpaper changer, https://launchpad.net/variety"

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.11 (KHTML, like Gecko) Ubuntu/12.04 Chromium/20.0.1132.47 Chrome/20.0.1132.47 Safari/536.11"

random.seed()
logger = logging.getLogger('variety')

class LogMethodCalls(object):
    def __init__(self, func, level):
        self.level = level
        self.func = func

    def __get__(self, obj, cls=None):
        def logcall(*func_args, **func_kwargs):
            logger.log(self.level, (cls.__name__ if cls else '')+ ": " + self.func.func_name +
                         '(' + ', '.join(map(str, func_args)) +
                         ((', %s' % func_kwargs) if func_kwargs else '') + ')')
            if inspect.isfunction(self.func) or inspect.isclass(self.func.im_self):
                ret = self.func(*func_args, **func_kwargs)
            else:
                ret = self.func(obj, *func_args, **func_kwargs)
            return ret
        for attr in "__module__", "__name__", "__doc__":
            setattr(logcall, attr, getattr(self.func, attr))
        return logcall


class Util:
    @staticmethod
    def log_all(cls, level=logging.DEBUG):
        if logger.isEnabledFor(level):
            for name, meth in inspect.getmembers(cls):
                if inspect.ismethod(meth) or inspect.isfunction(meth):
                    setattr(cls, name, LogMethodCalls(meth, level))
        return cls

    @staticmethod
    def get_local_name(url):
        filename = url[url.rindex('/') + 1:]
        index = filename.find('?')
        if index > 0:
            filename = filename[:index]
        index = filename.find('#')
        if index > 0:
            filename = filename[:index]

        filename = urllib.unquote_plus(filename)

        valid_chars = " ,.!-+@()_%s%s" % (string.ascii_letters, string.digits)
        filename = ''.join(c if c in valid_chars else '_' for c in filename)

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
        return filename.lower().endswith(('.jpg', '.jpeg', '.gif', '.png', '.tiff', '.svg', '.bmp'))

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
    def write_metadata(filename, info):
        try:
            pyexiv2.xmp.register_namespace("https://launchpad.net/variety/", "variety")
        except KeyError:
            pass

        try:
            m = pyexiv2.ImageMetadata(filename)
            m.read()
            m["Xmp.variety.info"] = VARIETY_INFO
            for k, v in info.items():
                m["Xmp.variety." + k] = v
            m.write()
            return True
        except Exception:
            # could not write metadata inside file, use txt instead
            try:
                with open(filename + ".txt", "w") as f:
                    f.write("INFO:\n%s\n%s\n%s\n%s\n%s\n" % (
                            info["sourceName"],
                            info["sourceURL"],
                            info["sourceLocation"],
                            info["imageURL"],
                            VARIETY_INFO))
            except Exception:
                logger.exception("Could not write url metadata for file " + filename)
            return False

    @staticmethod
    def read_metadata(filename):
        try:
            pyexiv2.xmp.register_namespace("https://launchpad.net/variety/", "variety")
        except KeyError:
            pass

        try:
            m = pyexiv2.ImageMetadata(filename)
            m.read()

            info = {}
            keys = ["sourceName", "sourceLocation", "sourceURL", "imageURL"]
            for k in keys:
                if "Xmp.variety." + k in m:
                    info[k] = m["Xmp.variety." + k].value
            return info
        except Exception, e:
            # could not read metadata inside file, use txt instead
            try:
                with open(filename + ".txt") as f:
                    lines = list(f)
                    info = {}
                    if len(lines) > 2 and lines[0].strip() == "INFO:":
                        info["sourceName"] = lines[1].strip().replace("Downloaded from ", "") # TODO remove later on
                        info["sourceURL"] = lines[2].strip()
                        if len(lines) > 3:
                            info["sourceLocation"] = lines[3].strip()
                        if len(lines) > 4:
                            info["imageURL"] = lines[4].strip()
                        return info
                    else:
                        return None
            except Exception:
                return None

    @staticmethod
    def set_rating(filename, rating):
        if rating is not None and (rating < -1 or rating > 5):
            raise ValueError("Rating should be between -1 and 5, or None")

        m = pyexiv2.ImageMetadata(filename)
        m.read()

        if rating is None:
            for key in ["Xmp.xmp.Rating", "Exif.Image.Rating", "Exif.Image.RatingPercent"]:
                if key in m:
                    del m[key]
        else:
            m["Xmp.xmp.Rating"] = rating
            m["Exif.Image.Rating"] = max(0, rating)
            if rating >= 1:
                m["Exif.Image.RatingPercent"] = (rating - 1) * 25
            elif "Exif.Image.RatingPercent" in m:
                del m["Exif.Image.RatingPercent"]

        m.write()

    @staticmethod
    def get_rating(filename):
        m = pyexiv2.ImageMetadata(filename)
        m.read()
        rating = None
        if "Xmp.xmp.Rating" in m:
            rating = m["Xmp.xmp.Rating"].value
        elif "Exif.Image.Rating" in m:
            rating = m["Exif.Image.Rating"].value
        elif "Exif.Image.RatingPercent" in m:
            rating = m["Exif.Image.RatingPercent"].value // 25 + 1
        if rating is not None:
            rating = max(-1, min(5, rating))
        return rating

    @staticmethod
    def get_size(image):
        try:
            d = DominantColors(image)
            return d.get_width(), d.get_height()
        except Exception:
            p = GdkPixbuf.Pixbuf.new_from_file(image)
            return p.get_width(), p.get_height()

    @staticmethod
    def find_unique_name(filename):
        index = filename.rfind('.')
        if index < 0:
            index = len(filename)
        before_extension = filename[:index]
        extension = filename[index:]
        i = 1
        f = filename
        while os.path.exists(f):
            f = before_extension + '_' + str(i) + extension
            i += 1
        return f

    @staticmethod
    def urlopen(url, data=None):
        request = urllib2.Request(url)
        request.add_header('User-Agent', USER_AGENT)
        request.add_header('Cache-Control', 'max-age=0')
        return urllib2.urlopen(request, data=data, timeout=20)

    @staticmethod
    def fetch(url, data=None):
        return Util.urlopen(url, data).read()

    @staticmethod
    def fetch_json(url, data=None):
        return json.loads(Util.fetch(url, data))

    @staticmethod
    def html_soup(url, data=None):
        return bs4.BeautifulSoup(Util.urlopen(url, data).read())

    @staticmethod
    def xml_soup(url, data=None):
        return bs4.BeautifulSoup(Util.urlopen(url, data).read(), "xml")

    @staticmethod
    def folderpath(folder):
        p = os.path.normpath(folder)
        if not p.endswith("/"):
            p += "/"
        return p

    @staticmethod
    def compute_trimmed_offsets(image_size, screen_size):
        """Computes what width or height of the wallpaper image will be trimmed on each side, as it is zoomed in to fill
        the whole screen. Returns a tuple (h, v, scale_ratio) in which h or v will be zero. The other one is the pixel
        width or height that will be trimmed on each one of the sides of the image (top and down or left and right)."""
        iw, ih = image_size
        screen_w, screen_h = screen_size
        screen_ratio = float(screen_w) / screen_h
        hoffset = voffset = 0
        if screen_ratio > float(iw) / ih: #image is "taller" than the screen ratio - need to offset vertically
            scaledw = float(screen_w)
            scaledh = ih * scaledw / iw
            voffset = int((scaledh - float(scaledw) / screen_ratio) / 2)
        else: #image is "wider" than the screen ratio - need to offset horizontally
            scaledh = float(screen_h)
            scaledw = iw * scaledh / ih
            hoffset = int((scaledw - float(scaledh) * screen_ratio) / 2)

        logger.info("Trimmed offsets debug info: w:%d, h:%d, ratio:%f, iw:%d, ih:%d, scw:%d, sch:%d, ho:%d, vo:%d" % (
            screen_w, screen_h, screen_ratio, iw, ih, scaledw, scaledh, hoffset, voffset))
        return hoffset, voffset

    @staticmethod
    def get_scaled_size(image):
        """Computes the size to which the image is scaled to fit the screen: original_size * scale_ratio = scaled_size"""
        iw, ih = Util.get_size(image)
        screen_w, screen_h = Gdk.Screen.get_default().get_width(), Gdk.Screen.get_default().get_height()
        screen_ratio = float(screen_w) / screen_h
        if screen_ratio > float(iw) / ih: #image is "taller" than the screen ratio - need to offset vertically
            return screen_w, int(round(ih * float(screen_w) / iw))
        else: #image is "wider" than the screen ratio - need to offset horizontally
            return int(round(iw * float(screen_h) / ih)), screen_h

    @staticmethod
    def get_scale_to_screen_ratio(image):
        """Computes the ratio by which the image is scaled to fit the screen: original_size * scale_ratio = scaled_size"""
        iw, ih = Util.get_size(image)
        screen_w, screen_h = Gdk.Screen.get_default().get_width(), Gdk.Screen.get_default().get_height()
        screen_ratio = float(screen_w) / screen_h
        if screen_ratio > float(iw) / ih: #image is "taller" than the screen ratio - need to offset vertically
            return int(float(screen_w) / iw)
        else: #image is "wider" than the screen ratio - need to offset horizontally
            return int(float(screen_h) / ih)

    @staticmethod
    def gtk_to_fcmatch_font(gtk_font_name):
        fd = Pango.FontDescription(gtk_font_name)
        family = fd.get_family()
        size = gtk_font_name[gtk_font_name.rindex(' '):].strip()
        rest = gtk_font_name.replace(family, '').strip().replace(' ', ':')
        return family + ":" + rest, size

    @staticmethod
    def file_in(file, folder):
        return os.path.normpath(file).startswith(os.path.normpath(folder))

    @staticmethod
    def same_file_paths(f1, f2):
        return os.path.normpath(f1) == os.path.normpath(f2)

    @staticmethod
    def collapseuser(path):
        home = os.path.expanduser('~') + '/'
        return re.sub('^' + home, '~/', path)

    @staticmethod
    def compare_versions(v1, v2):
        def _score(v):
            a = map(int, v.split('.'))
            while len(a) < 3:
                a.append(0)
            return a[0] * 10**6 + a[1] * 10**3 + a[2]
        s1 = _score(v1)
        s2 = _score(v2)
        return -1 if s1 < s2 else (0 if s1 == s2 else 1)

    @staticmethod
    def md5(s):
        return hashlib.md5(s).hexdigest()

    @staticmethod
    def md5file(file):
        with open(file) as f:
            return Util.md5(f.read())

    @staticmethod
    def random_hash():
        try:
            return os.urandom(16).encode('hex')
        except Exception:
            return ''.join(random.choice(string.hexdigits) for n in xrange(32))

    @staticmethod
    def get_file_icon_name(path):
        try:
            from gi.repository import Gio
            f = Gio.File.new_for_path(path)
            query_info = f.query_info("standard::icon", Gio.FileQueryInfoFlags.NONE, None)
            return query_info.get_attribute_object("standard::icon").get_names()[0]
        except Exception:
            logger.exception("Exception while obtaining folder icon for %s:" % path)
            return "folder"
