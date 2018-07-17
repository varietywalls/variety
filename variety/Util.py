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
import requests
from functools import wraps
import hashlib
import io
import json
import re
import os
import random
import logging
import string
import threading
import time
import urllib.request, urllib.parse, urllib.error
import functools
import datetime
from urllib.parse import urlparse
from PIL import Image

from .DominantColors import DominantColors

import gi
gi.require_version('GExiv2', '0.10')
gi.require_version('PangoCairo', '1.0')

from gi.repository import Gdk, Pango, GdkPixbuf, GLib, GExiv2
import inspect
import subprocess
import platform
from variety import _u, _str


VARIETY_INFO = "-"

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36"

SOURCE_NAME_TO_TYPE = {
    'wallbase.cc': 'wallbase',
    'wallhaven.cc': 'wallhaven',
    'wallpapers.net': 'wn',
    'desktoppr.co': 'desktoppr',
    'nasa astro pic of the day': 'apod',
    'opentopia.com': 'earth',
    'fetched': 'fetched',
    'recommended by variety': 'recommended',
    'flickr': 'flickr',
    'media rss': 'mediarss',
}

random.seed()
logger = logging.getLogger('variety')

class LogMethodCalls(object):
    def __init__(self, func, level):
        self.level = level
        self.func = func

    def __get__(self, obj, cls=None):
        def logcall(*func_args, **func_kwargs):
            logger.log(self.level, (cls.__name__ if cls else '')+ ": " + self.func.__name__ +
                         '(' + ', '.join(map(_str, func_args)) +
                         ((', %s' % func_kwargs) if func_kwargs else '') + ')')
            if inspect.isfunction(self.func) or inspect.isclass(self.func.__self__):
                ret = self.func(*func_args, **func_kwargs)
            else:
                ret = self.func(obj, *func_args, **func_kwargs)
            return ret
        for attr in "__module__", "__name__", "__doc__":
            setattr(logcall, attr, getattr(self.func, attr))
        return logcall


def debounce(seconds):
    """ Decorator that will postpone a functions execution until after wait seconds
        have elapsed since the last time it was invoked. """
    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                fn(*args, **kwargs)
            try:
                debounced.t.cancel()
            except(AttributeError):
                pass
            debounced.t = threading.Timer(seconds, call_it)
            debounced.t.start()
        return debounced
    return decorator


class throttle(object):
    """
    Decorator that prevents a function from being called more than once every time period. Allows for a trailing call.

    To create a function that cannot be called more than once a minute:

        @throttle(seconds=1)
        def my_fun():
            pass
    """
    def __init__(self, seconds=0, trailing_call=False):
        """
        seconds - throttle interval in seconds
        trailing - if True, there will always be a call seconds after the last call
        """
        self.seconds = seconds
        self.trailing_call = trailing_call
        self.time_of_last_call = 0
        self.timer = None

    def __call__(self, fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                self.timer.cancel()
            except:
                pass

            def call_it():
                self.time_of_last_call = time.time()
                return fn(*args, **kwargs)

            seconds_since_last_call = time.time() - self.time_of_last_call
            if seconds_since_last_call >= self.seconds:
                return call_it()
            elif self.trailing_call:
                self.timer = threading.Timer(self.seconds - seconds_since_last_call, call_it)
                self.timer.start()

        return wrapper


def cache(ttl_seconds=100*365*24*3600, debug=False):
    """
    caching decorator with TTL. Keep in mind the cache is per-process.
    TODO: There is no process for cache invalidation now. Introduce memcached and use it instead.
    :param ttl_seconds: TTL in seconds before the cache entry expires
    :param debug: use True to log cache hits (with DEBUG level)
    """
    def decorate(f):
        _cache = {}

        @functools.wraps(f)
        def decorated(*args):
            cached = _cache.get(args)
            if not cached or cached['timestamp'] < datetime.datetime.now() - datetime.timedelta(seconds=ttl_seconds):
                cached = {
                    'timestamp': datetime.datetime.now(),
                    'result': f(*args)
                }
                _cache[args] = cached
            elif debug:
                logger.debug(lambda: '@cache hit for %s' % str(args))
            return cached['result']
        return decorated

    return decorate


class VarietyMetadata(GExiv2.Metadata):
    MULTIPLES = {
        "Iptc.Application2.Headline",
        "Iptc.Application2.Keywords",
        "Xmp.dc.creator",
        "Xmp.dc.subject",
    }

    NUMBERS = {
        "Xmp.variety.sfwRating",
        "Xmp.xmp.Rating",
        "Exif.Image.Rating",
        "Exif.Image.RatingPercent",
    }

    def __init__(self, path):
        super(VarietyMetadata, self).__init__(path=path)
        self.register_xmp_namespace("https://launchpad.net/variety/", "variety")

    def __getitem__(self, key):
        if self.has_tag(key):
            if key in self.MULTIPLES:
                return self.get_tag_multiple(key)
            elif key in self.NUMBERS:
                return self.get_tag_long(key)
            else:
                return self.get_tag_string(key)
        else:
            raise KeyError('%s: Unknown tag' % key)

    def __setitem__(self, key, value):
        if key in self.MULTIPLES:
            self.set_tag_multiple(key, value)
        elif key in self.NUMBERS:
            self.set_tag_long(key, value)
        else:
            self.set_tag_string(key, value)


class Util:
    @staticmethod
    def log_all(cls, level=logging.DEBUG):
        if logger.isEnabledFor(level):
            for name, meth in inspect.getmembers(cls):
                if inspect.ismethod(meth) or inspect.isfunction(meth):
                    setattr(cls, name, LogMethodCalls(meth, level))
        return cls

    @staticmethod
    def sanitize_filename(filename):
        valid_chars = " ,.!-+@()_%s%s" % (string.ascii_letters, string.digits)
        return ''.join(c if c in valid_chars else '_' for c in filename)

    @staticmethod
    def get_local_name(url, ensure_image=True):
        filename = url[url.rfind('/') + 1:]
        index = filename.find('?')
        if index > 0:
            filename = filename[:index]
        index = filename.find('#')
        if index > 0:
            filename = filename[:index]

        filename = urllib.parse.unquote_plus(filename)

        filename = Util.sanitize_filename(filename)

        if len(filename) > 200:
            filename = filename[:190] + filename[-10:]

        if ensure_image and not Util.is_image(filename):
            filename += '.jpg'

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
            if not os.path.isdir(path):
                logger.info(lambda: "Creating folder %s" % path)
                os.makedirs(path)
        except OSError:
            logger.exception(lambda: "Could not makedirs for %s" % path)

    @staticmethod
    def is_image(filename, check_contents=False):
        if Util.is_animated_gif(filename):
            return False

        if not check_contents:
            return filename.lower().endswith(('.jpg', '.jpeg', '.gif', '.png', '.tiff', '.svg', '.bmp'))
        else:
            format, image_width, image_height = GdkPixbuf.Pixbuf.get_file_info(filename)
            return bool(format)

    @staticmethod
    def is_animated_gif(filename):
        if not filename.lower().endswith('.gif'):
            return False

        gif = Image.open(filename)
        try:
            gif.seek(1)
        except EOFError:
            return False
        else:
            return True

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
                                    logger.info(lambda: "More than %d files in the folders, stop listing" % max_files)
                                    return
                                yield os.path.join(root, filename)
                except Exception:
                    logger.exception(lambda: "Cold not walk folder " + folder)

    @staticmethod
    def start_force_exit_thread(delay):
        def force_exit():
            time.sleep(delay)
            print("Exiting takes too long. Calling os.kill.")
            os.kill(os.getpid(), 9)
        force_exit_thread = threading.Thread(target=force_exit)
        force_exit_thread.daemon = True
        force_exit_thread.start()

    @staticmethod
    def check_and_update_metadata(filename):
        if not Util.is_image(filename):
            # Skip working on stuff that isn't a picture; part of https://bugs.debian.org/893759
            return False

        try:
            m = VarietyMetadata(filename)
        except Exception:
            logger.exception(lambda: "Could not read metadata for %s" % filename)
            return False

        try:
            if 'Xmp.variety.info' in m or 'vrty.org' in m.get('imageURL', ''):
                logger.info(lambda: 'Updating metadata for %s' % filename)
                del m["Xmp.variety.info"]
                if 'imageURL' in m and 'vrty.org' in m['imageURL']:
                    del m['imageURL']
                m.write(preserve_timestamps=True)

                return True
        except Exception:
            logger.exception(lambda: "Could not read metadata for %s" % filename)

        return False

    @staticmethod
    def write_metadata(filename, info):
        try:
            m = VarietyMetadata(filename)
            for k, v in list(info.items()):
                if k == 'author':
                    m["Xmp.variety." + k] = v
                    if not 'Xmp.dc.creator' in m:
                        m['Xmp.dc.creator'] = [v]
                if k == 'headline':
                    m['Iptc.Application2.Headline'] = [v]
                elif k == 'description':
                    if v is not None:
                        m.set_comment(v)
                    else:
                        m.clear_comment()
                elif k == 'keywords':
                    if not isinstance(v, (list, tuple)):
                        v = [v]
                    m['Iptc.Application2.Keywords'] = v
                    m['Xmp.dc.subject'] = v
                elif k == 'sfwRating':
                    m["Xmp.variety." + k] = int(v)
                elif k == 'extraData':
                    m["Xmp.variety." + k] = json.dumps(v)
                else:
                    m["Xmp.variety." + k] = v
            m.save_file()
            return True
        except Exception as ex:
            # could not write metadata inside file, use json instead
            logger.exception(lambda: "Could not write metadata directly in file, trying json metadata: " + filename)
            try:
                with io.open(filename + '.metadata.json', 'w', encoding='utf8') as f:
                    f.write(json.dumps(info, indent=4, ensure_ascii=False, encoding='utf8'))
                    return True
            except Exception as e:
                logger.exception(lambda: "Could not write metadata for file " + filename)
                return False

    @staticmethod
    def read_metadata(filename):
        try:
            m = VarietyMetadata(filename)

            info = {}
            for k in ["sourceName", "sourceLocation", "sourceURL", "sourceType", "imageURL", "author", "authorURL"]:
                if "Xmp.variety." + k in m:
                    info[k] = _u(m["Xmp.variety." + k])

            try:
                info['sfwRating'] = int(m['Xmp.variety.sfwRating'])
            except:
                pass

            try:
                info['author'] = _u(m['Xmp.dc.creator'][0])
            except:
                pass

            try:
                info['headline'] = _u(m['Iptc.Application2.Headline'][0])
            except:
                pass

            try:
                info['description'] = _u(m.get_comment())
            except:
                pass

            try:
                info['extraData'] = json.loads(m['Xmp.variety.extraData'])
            except:
                pass

            try:
                info['keywords'] = list(map(_u, m['Iptc.Application2.Keywords']))
            except:
                try:
                    info['keywords'] = list(map(_u, m['Xmp.dc.subject']))
                except:
                    pass

            return info

        except Exception as e:
            # could not read metadata inside file, try reading json metadata instead
            try:
                with io.open(filename + '.metadata.json', encoding='utf8') as f:
                    return json.loads(f.read())

            except Exception:
                return None

    @staticmethod
    def set_rating(filename, rating):
        if rating is not None and (rating < -1 or rating > 5):
            raise ValueError("Rating should be between -1 and 5, or None")

        m = VarietyMetadata(filename)

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

        m.save_file()

    @staticmethod
    def get_rating(filename):
        m = VarietyMetadata(filename)
        rating = None
        if "Xmp.xmp.Rating" in m:
            rating = m["Xmp.xmp.Rating"]
        elif "Exif.Image.Rating" in m:
            rating = m["Exif.Image.Rating"]
        elif "Exif.Image.RatingPercent" in m:
            rating = m["Exif.Image.RatingPercent"] // 25 + 1
        if rating is not None:
            rating = max(-1, min(5, rating))
        return rating

    @staticmethod
    def get_size(image):
        format, image_width, image_height = GdkPixbuf.Pixbuf.get_file_info(image)
        if not format:
            raise Exception('Not an image or unsupported image format')
        else:
            return image_width, image_height

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
    def request(url, data=None, stream=False, method=None):
        if url.startswith('//'):
            url = 'http:' + url
        headers = {
            'User-Agent': USER_AGENT,
            'Cache-Control': 'max-age=0'
        }
        method = method if method else 'POST' if data else 'GET'
        try:
            r = requests.request(method=method,
                                 url=url,
                                 data=data,
                                 headers=headers,
                                 stream=stream,
                                 allow_redirects=True,
                                 verify=False)
            r.raise_for_status()
            return r
        except requests.exceptions.SSLError:
            logger.exception('SSL Error for url %s:' % url)
            raise

    @staticmethod
    def request_write_to(r, f):
        for chunk in r.iter_content(1024):
            f.write(chunk)

    @staticmethod
    def fetch(url, data=None):
        return Util.request(url, data).text

    @staticmethod
    def fetch_bytes(url, data=None):
        return Util.request(url, data).content

    @staticmethod
    def fetch_json(url, data=None):
        return Util.request(url, data).json()

    @staticmethod
    def html_soup(url, data=None):
        return bs4.BeautifulSoup(Util.fetch(url, data))

    @staticmethod
    def xml_soup(url, data=None):
        return bs4.BeautifulSoup(Util.fetch(url, data), "xml")

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

        logger.info(lambda: "Trimmed offsets debug info: w:%d, h:%d, ratio:%f, iw:%d, ih:%d, scw:%d, sch:%d, ho:%d, vo:%d" % (
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
        family = _u(fd.get_family())
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
            a = list(map(int, v.split('.')))
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
            return ''.join(random.choice(string.hexdigits) for n in range(32))

    @staticmethod
    def get_file_icon_name(path):
        try:
            from gi.repository import Gio
            f = Gio.File.new_for_path(os.path.normpath(os.path.expanduser(path)))
            query_info = f.query_info("standard::icon", Gio.FileQueryInfoFlags.NONE, None)
            return query_info.get_attribute_object("standard::icon").get_names()[0]
        except Exception:
            logger.exception(lambda: "Exception while obtaining folder icon for %s:" % path)
            return "folder"

    @staticmethod
    def is_home_encrypted():
        return os.path.isdir(os.path.expanduser("~").replace('/home/', '/home/.ecryptfs/'))

    @staticmethod
    def get_xdg_pictures_folder():
        try:
            pics_folder = GLib.get_user_special_dir(GLib.USER_DIRECTORY_PICTURES)
            if not pics_folder:
                raise Exception("Could not get path to Pictures folder. Defaulting to ~/Pictures.")
            return pics_folder
        except:
            logger.exception(lambda: "Could not get path to Pictures folder. Defaulting to ~/Pictures.")
            return os.path.expanduser('~/Pictures')

    @staticmethod
    def superuser_exec(*command_args):
        logger.warning(lambda: "Executing as superuser: %s" % _str(command_args))
        subprocess.check_call(["pkexec"] + list(command_args))

    @staticmethod
    def safe_map(f, l):
        for element in l:
            try:
                yield f(element)
            except Exception:
                continue

    @staticmethod
    def get_thumbnail_data(image, width, height):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(image, width, height)
        return pixbuf.save_to_bufferv('jpeg', [], [])[1]

    @staticmethod
    def is_alive_and_image(url):
        try:
            r = Util.request(url, method='head')
            return r.headers.get('content-type', '').startswith('image/')
        except Exception:
            return False

    @staticmethod
    def is_dead_or_not_image(url):
        if not url:
            return True

        try:
            host = urlparse(url).netloc
            if host.startswith('interfacelift.com'):
                return False

            if 'wallbase.cc' in host or 'ns223506.ovh.net' in host:
                return True
        except:
            return True

        try:
            r = Util.request(url, method='head')
            return not r.headers.get('content-type', '').startswith('image/')
        except requests.exceptions.RequestException:
            return True
        except:
            return False

    @staticmethod
    def guess_image_url(meta):
        if 'imageURL' in meta:
            return meta['imageURL']

        try:
            origin_url = meta['sourceURL']

            if "flickr.com" in origin_url:
                from variety.FlickrDownloader import FlickrDownloader
                return FlickrDownloader.get_image_url(origin_url)

            elif Util.is_image(origin_url) and Util.is_alive_and_image(origin_url):
                return origin_url

            return None
        except:
            return None

    @staticmethod
    def guess_source_type(meta):
        try:
            if 'sourceType' in meta:
                return meta['sourceType']
            elif 'sourceName' in meta:
                source_name = meta['sourceName'].lower()
                if source_name in SOURCE_NAME_TO_TYPE:
                    return SOURCE_NAME_TO_TYPE[source_name]
                else:
                    source_location = meta.get('sourceLocation', '').lower()
                    if source_location.startswith(('http://' + source_name, 'https://' + source_name)) \
                            or 'backend.deviantart.com' in source_location \
                            or 'rss' in source_location \
                            or '/feed' in source_location:
                        return 'mediarss'
            return None
        except:
            return None

    @staticmethod
    def get_os_name():
        return ' '.join(platform.linux_distribution()[0:2])

    # makes the Gtk thread execute the given callback.
    @staticmethod
    def add_mainloop_task(callback, *args):
        def cb(args):
            args[0](*args[1:])
            return False
        args= [callback]+list(args)
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT, cb, args)

    @staticmethod
    def is_unity():
        return os.getenv('XDG_CURRENT_DESKTOP', '').lower() == 'unity'

    @staticmethod
    def start_daemon(target):
        daemon_thread = threading.Thread(target=target)
        daemon_thread.daemon = True
        daemon_thread.start()
        return daemon_thread

