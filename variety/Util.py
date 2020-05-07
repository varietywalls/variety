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
import base64
import codecs
import datetime
import functools
import gettext
import hashlib
import json
import logging
import os
import random
import re
import shutil
import string
import subprocess
import sys
import threading
import time
import urllib.parse
from itertools import cycle

import bs4
import requests
from PIL import Image

from variety_lib import get_version

# fmt: off
import gi  # isort:skip
gi.require_version("GExiv2", "0.10")
gi.require_version("PangoCairo", "1.0")
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GdkPixbuf, GExiv2, Gio, GLib, Pango  # isort:skip
# fmt: on


USER_AGENT = "Variety Wallpaper Changer " + get_version()

random.seed()
logger = logging.getLogger("variety")
gettext.textdomain("variety")


def _(text):
    """Returns the translated form of text."""
    if not text or not text.strip():
        return text
    return gettext.gettext(text)


def debounce(seconds):
    """ Decorator that will postpone a functions execution until after wait seconds
        have elapsed since the last time it was invoked. """

    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                fn(*args, **kwargs)

            try:
                debounced.t.cancel()
            except (AttributeError):
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
        @functools.wraps(fn)
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


def cache(ttl_seconds=100 * 365 * 24 * 3600, debug=False):
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
            if not cached or cached["timestamp"] < datetime.datetime.now() - datetime.timedelta(
                seconds=ttl_seconds
            ):
                cached = {"timestamp": datetime.datetime.now(), "result": f(*args)}
                _cache[args] = cached
            elif debug:
                logger.debug(lambda: "@cache hit for %s" % str(args))
            return cached["result"]

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
            raise KeyError("%s: Unknown tag" % key)

    def __setitem__(self, key, value):
        if key in self.MULTIPLES:
            self.set_tag_multiple(key, value)
        elif key in self.NUMBERS:
            self.set_tag_long(key, value)
        else:
            self.set_tag_string(key, value)


class ModuleProfiler:
    # How deep in other modules' code we should profile
    MAX_NONTARGET_DEPTH = 1

    def __init__(self):
        """
        Initializes the module profiler.
        """
        self.target_paths = []

        # Track how far deep we are in functions outside our target packages
        # The intent is to only log the first call to outside methods without following them further
        self.nontarget_depths = {}

    def log_class(self, cls):
        """
        Adds the given class' module to the list of modules to be profiled.
        """
        modulename = cls.__module__
        if modulename not in sys.modules:
            logger.error(
                "ModuleProfiler: Could not add module %r (class %s) to the list of modules to trace - "
                "has it been imported entirely?",
                modulename,
                cls,
            )
            return

        module = sys.modules[modulename]

        self.log_module(module, request=cls)

    def log_module(self, module, request=None):
        """
        Adds the given module to the list of modules to be profiled.
        """
        self.log_path(module.__file__, request=request)

    def log_path(self, path, request=None):
        """
        Adds the given module path to the list of profile targets.
        """
        self.target_paths.append(path)

        logger.info(
            "ModuleProfiler: added path %s to list of profile targets (request=%s)", path, request
        )

    @functools.lru_cache(maxsize=2048)
    def is_target_path(self, path):
        """
        Returns whether the given path matches one of our modules to be profiled.
        """
        for target in self.target_paths:
            if os.path.isdir(target) and path.startswith(target + os.path.sep):
                return True
            elif path == target:
                return True
        return False

    def start(self):
        """
        Starts the module profiler for all future threads.
        """
        threading.setprofile(self.profiler)

    def stop(self):
        """
        Removes the module profiler globally and from future threads.
        """
        if sys.getprofile() != self.profiler:
            logger.warning(
                "ModuleProfiler: The currently enabled profile function was not ours - unbinding anyways"
            )
        threading.setprofile(None)
        sys.setprofile(None)

    def profiler(self, frame, event, arg):
        filename = frame.f_code.co_filename

        tid = threading.get_ident()

        if not self.is_target_path(filename):
            if tid not in self.nontarget_depths:
                # Pick up where the main thread left off
                self.nontarget_depths[tid] = self.nontarget_depths.get(
                    threading.main_thread().ident, 1
                )
            else:
                self.nontarget_depths[tid] += 1
        else:
            self.nontarget_depths[tid] = 0

        tname = threading.current_thread().name

        if event == "call":
            if self.nontarget_depths[tid] > self.MAX_NONTARGET_DEPTH:
                # Don't log past our max depth for packages that we're not tracking
                return
            else:
                # In order: function name, line number, filename
                s = "[%s] -> Entering function: %s\t(line %s in %s)" % (
                    tname,
                    frame.f_code.co_name,
                    frame.f_lineno,
                    filename,
                )
                if self.nontarget_depths[tid] == self.MAX_NONTARGET_DEPTH:
                    s += (
                        " - not tracing further because MAX_NONTARGET_DEPTH=%s"
                        % self.MAX_NONTARGET_DEPTH
                    )
                logger.debug(s)

        elif event == "return":
            if self.nontarget_depths[tid] > self.MAX_NONTARGET_DEPTH:
                return

            logger.debug(
                "[%s] -> Leaving function:  %s\t(line %s in %s)"
                % (tname, frame.f_code.co_name, frame.f_lineno, filename)
            )


class Util:
    @staticmethod
    def sanitize_filename(filename):
        valid_chars = " ,.!-+@()_%s%s" % (string.ascii_letters, string.digits)
        return "".join(c if c in valid_chars else "_" for c in filename)

    @staticmethod
    def get_local_name(url, ensure_image=True):
        filename = url[url.rfind("/") + 1 :]
        index = filename.find("?")
        if index > 0:
            filename = filename[:index]
        index = filename.find("#")
        if index > 0:
            filename = filename[:index]

        filename = urllib.parse.unquote_plus(filename)

        filename = Util.sanitize_filename(filename)

        if len(filename) > 200:
            filename = filename[:190] + filename[-10:]

        if ensure_image and not Util.is_image(filename):
            filename += ".jpg"

        return filename

    @staticmethod
    def split(s, seps=(",", " ")):
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
            return filename.lower().endswith(
                (".jpg", ".jpeg", ".gif", ".png", ".tiff", ".svg", ".bmp")
            )
        else:
            format, image_width, image_height = GdkPixbuf.Pixbuf.get_file_info(filename)
            return bool(format)

    @staticmethod
    def is_animated_gif(filename):
        if not filename.lower().endswith(".gif"):
            return False

        gif = Image.open(filename)
        try:
            gif.seek(1)
        except EOFError:
            return False
        else:
            return True

    @staticmethod
    def list_files(
        files=(), folders=(), filter_func=(lambda f: True), max_files=10000, randomize=True
    ):
        count = 0
        for filepath in files:
            logger.debug(
                lambda: "checking file %s against filter_func %s" % (filepath, filter_func)
            )
            if filter_func(filepath) and os.access(filepath, os.R_OK):
                count += 1
                yield filepath

        folders = list(folders)
        if randomize:
            random.shuffle(folders)

        for folder in folders:
            if os.path.isdir(folder):
                try:
                    for root, subFolders, files in os.walk(folder, followlinks=True):
                        if randomize:
                            random.shuffle(files)
                            random.shuffle(subFolders)
                        for filename in files:
                            logger.debug(
                                lambda: "checking file %s against filter_func %s (root=%s)"
                                % (filename, filter_func, root)
                            )
                            path = os.path.join(root, filename)
                            if filter_func(path):
                                count += 1
                                if count > max_files:
                                    logger.info(
                                        lambda: "More than %d files in the folders, stop listing"
                                        % max_files
                                    )
                                    return
                                yield path
                except Exception:
                    logger.exception(lambda: "Could not walk folder " + folder)

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
    def write_metadata(filename, info):
        try:
            m = VarietyMetadata(filename)
            for k, v in sorted(info.items()):
                if k == "author":
                    m["Xmp.variety." + k] = v
                    if not "Xmp.dc.creator" in m:
                        m["Xmp.dc.creator"] = [v]
                if k == "headline":
                    m["Iptc.Application2.Headline"] = [v]
                elif k == "description":
                    if v is not None:
                        m.set_comment(v)
                    else:
                        m.clear_comment()
                elif k == "keywords":
                    if not isinstance(v, (list, tuple)):
                        v = [v]
                    m["Iptc.Application2.Keywords"] = v
                    m["Xmp.dc.subject"] = v
                elif k == "sfwRating":
                    m["Xmp.variety." + k] = int(v)
                elif k == "extraData":
                    m["Xmp.variety." + k] = json.dumps(v, sort_keys=True)
                else:
                    m["Xmp.variety." + k] = v
            m.save_file()
            return True
        except Exception as ex:
            # could not write metadata inside file, use json instead
            logger.exception(
                lambda: "Could not write metadata directly in file, trying json metadata: "
                + filename
            )
            try:
                with open(filename + ".metadata.json", "w", encoding="utf8") as f:
                    f.write(json.dumps(info, indent=4, ensure_ascii=False, sort_keys=True))
                    return True
            except Exception as e:
                logger.exception(lambda: "Could not write metadata for file " + filename)
                return False

    @staticmethod
    def read_metadata(filename):
        try:
            m = VarietyMetadata(filename)

            info = {}
            for k in [
                "sourceName",
                "sourceLocation",
                "sourceURL",
                "sourceType",
                "imageURL",
                "author",
                "authorURL",
                "noOriginPage",
            ]:
                if "Xmp.variety." + k in m:
                    info[k] = m["Xmp.variety." + k]

            try:
                info["sfwRating"] = int(m["Xmp.variety.sfwRating"])
            except:
                pass

            try:
                info["author"] = m["Xmp.dc.creator"][0]
            except:
                pass

            try:
                info["headline"] = m["Iptc.Application2.Headline"][0]
            except:
                pass

            try:
                info["description"] = m.get_comment()
            except:
                pass

            try:
                info["extraData"] = json.loads(m["Xmp.variety.extraData"])
            except:
                pass

            try:
                info["keywords"] = m["Iptc.Application2.Keywords"]
            except:
                try:
                    info["keywords"] = m["Xmp.dc.subject"]
                except:
                    pass

            return info

        except Exception as e:
            # could not read metadata inside file, try reading json metadata instead
            try:
                with open(filename + ".metadata.json", encoding="utf8") as f:
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
                    del m[key]  # pylint: disable=unsupported-delete-operation
        else:
            m["Xmp.xmp.Rating"] = rating
            m["Exif.Image.Rating"] = max(0, rating)
            if rating >= 1:
                m["Exif.Image.RatingPercent"] = (rating - 1) * 25
            elif "Exif.Image.RatingPercent" in m:
                del m["Exif.Image.RatingPercent"]  # pylint: disable=unsupported-delete-operation

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
            raise Exception("Not an image or unsupported image format")
        else:
            return image_width, image_height

    @staticmethod
    def find_unique_name(filename):
        index = filename.rfind(".")
        if index < 0:
            index = len(filename)
        before_extension = filename[:index]
        extension = filename[index:]
        i = 1
        f = filename
        while os.path.exists(f):
            f = before_extension + "_" + str(i) + extension
            i += 1
        return f

    @staticmethod
    def request(url, data=None, stream=False, method=None, timeout=5, headers=None):
        if url.startswith("//"):
            url = "http:" + url
        headers = headers or {}
        headers = {"User-Agent": USER_AGENT, "Cache-Control": "max-age=0", **headers}
        method = method if method else "POST" if data else "GET"
        try:
            r = requests.request(
                method=method,
                url=url,
                data=data,
                headers=headers,
                stream=stream,
                allow_redirects=True,
                timeout=timeout,
            )
            r.raise_for_status()
            return r
        except requests.exceptions.SSLError:
            logger.exception("SSL Error for url %s:" % url)
            raise

    @staticmethod
    def request_write_to(r, f):
        for chunk in r.iter_content(1024):
            f.write(chunk)

    @staticmethod
    def fetch(url, data=None, **request_kwargs):
        return Util.request(url, data, **request_kwargs).text

    @staticmethod
    def fetch_bytes(url, data=None, **request_kwargs):
        return Util.request(url, data, **request_kwargs).content

    @staticmethod
    def fetch_json(url, data=None, **request_kwargs):
        return Util.request(url, data, **request_kwargs).json()

    @staticmethod
    def html_soup(url, data=None, **request_kwargs):
        return bs4.BeautifulSoup(Util.fetch(url, data, **request_kwargs), "lxml")

    @staticmethod
    def xml_soup(url, data=None, **request_kwargs):
        return bs4.BeautifulSoup(Util.fetch(url, data, **request_kwargs), "xml")

    @staticmethod
    def unxor(text, key):
        ciphertext = base64.decodestring(text)
        return "".join(chr(x ^ ord(y)) for (x, y) in zip(ciphertext, cycle(key)))

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
        if (
            screen_ratio > float(iw) / ih
        ):  # image is "taller" than the screen ratio - need to offset vertically
            scaledw = float(screen_w)
            scaledh = ih * scaledw / iw
            voffset = int((scaledh - float(scaledw) / screen_ratio) / 2)
        else:  # image is "wider" than the screen ratio - need to offset horizontally
            scaledh = float(screen_h)
            scaledw = iw * scaledh / ih
            hoffset = int((scaledw - float(scaledh) * screen_ratio) / 2)

        logger.info(
            lambda: "Trimmed offsets debug info: w:%d, h:%d, ratio:%f, iw:%d, ih:%d, scw:%d, sch:%d, ho:%d, vo:%d"
            % (screen_w, screen_h, screen_ratio, iw, ih, scaledw, scaledh, hoffset, voffset)
        )
        return hoffset, voffset

    @staticmethod
    def get_scaled_size(image):
        """Computes the size to which the image is scaled to fit the screen: original_size * scale_ratio = scaled_size"""
        iw, ih = Util.get_size(image)
        screen_w, screen_h = (
            Gdk.Screen.get_default().get_width(),
            Gdk.Screen.get_default().get_height(),
        )
        screen_ratio = float(screen_w) / screen_h
        if (
            screen_ratio > float(iw) / ih
        ):  # image is "taller" than the screen ratio - need to offset vertically
            return screen_w, int(round(ih * float(screen_w) / iw))
        else:  # image is "wider" than the screen ratio - need to offset horizontally
            return int(round(iw * float(screen_h) / ih)), screen_h

    @staticmethod
    def get_scale_to_screen_ratio(image):
        """Computes the ratio by which the image is scaled to fit the screen: original_size * scale_ratio = scaled_size"""
        iw, ih = Util.get_size(image)
        screen_w, screen_h = (
            Gdk.Screen.get_default().get_width(),
            Gdk.Screen.get_default().get_height(),
        )
        screen_ratio = float(screen_w) / screen_h
        if (
            screen_ratio > float(iw) / ih
        ):  # image is "taller" than the screen ratio - need to offset vertically
            return int(float(screen_w) / iw)
        else:  # image is "wider" than the screen ratio - need to offset horizontally
            return int(float(screen_h) / ih)

    @staticmethod
    def gtk_to_fcmatch_font(gtk_font_name):
        fd = Pango.FontDescription(gtk_font_name)
        family = fd.get_family()
        size = gtk_font_name[gtk_font_name.rindex(" ") :].strip()
        rest = gtk_font_name.replace(family, "").strip().replace(" ", ":")
        return family + ":" + rest, size

    @staticmethod
    def file_in(file, folder):
        return os.path.normpath(file).startswith(os.path.normpath(folder))

    @staticmethod
    def same_file_paths(f1, f2):
        return os.path.normpath(f1) == os.path.normpath(f2)

    @staticmethod
    def collapseuser(path):
        home = os.path.expanduser("~") + "/"
        return re.sub("^" + home, "~/", path)

    @staticmethod
    def compare_versions(v1, v2):
        from pkg_resources import parse_version

        pv1 = parse_version(v1)
        pv2 = parse_version(v2)

        if pv1 == pv2:
            return 0
        else:
            return -1 if pv1 < pv2 else 1

    @staticmethod
    def md5(s):
        if isinstance(s, str):
            s = s.encode("utf-8")
        return hashlib.md5(s).hexdigest()

    @staticmethod
    def md5file(file):
        with open(file, mode="rb") as f:
            return Util.md5(f.read())

    @staticmethod
    def random_hash():
        try:
            return codecs.encode(os.urandom(16), "hex_codec").decode("utf8")
        except Exception:
            return "".join(random.choice(string.hexdigits) for _ in range(32)).lower()

    @staticmethod
    def get_file_icon_name(path):
        try:
            f = Gio.File.new_for_path(os.path.normpath(os.path.expanduser(path)))
            query_info = f.query_info("standard::icon", Gio.FileQueryInfoFlags.NONE, None)
            return query_info.get_attribute_object("standard::icon").get_names()[0]
        except Exception:
            logger.exception(lambda: "Exception while obtaining folder icon for %s:" % path)
            return "folder"

    @staticmethod
    def is_home_encrypted():
        return os.path.isdir(os.path.expanduser("~").replace("/home/", "/home/.ecryptfs/"))

    @staticmethod
    def get_xdg_pictures_folder():
        try:
            pics_folder = GLib.get_user_special_dir(GLib.USER_DIRECTORY_PICTURES)
            if not pics_folder:
                raise Exception("Could not get path to Pictures folder. Defaulting to ~/Pictures.")
            return pics_folder
        except:
            logger.exception(
                lambda: "Could not get path to Pictures folder. Defaulting to ~/Pictures."
            )
            return os.path.expanduser("~/Pictures")

    @staticmethod
    def superuser_exec(*command_args):
        logger.warning(lambda: "Executing as superuser: %s" % command_args)
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
        return pixbuf.save_to_bufferv("jpeg", [], [])[1]

    @staticmethod
    def is_alive_and_image(url):
        try:
            r = Util.request(url, method="head")
            return r.headers.get("content-type", "").startswith("image/")
        except Exception:
            return False

    @staticmethod
    def is_dead_or_not_image(url):
        if not url:
            return True

        try:
            host = urllib.parse.urlparse(url).netloc
            if host.startswith("interfacelift.com"):
                return False

            if "wallbase.cc" in host or "ns223506.ovh.net" in host:
                return True
        except:
            return True

        try:
            r = Util.request(url, method="head")
            return not r.headers.get("content-type", "").startswith("image/")
        except requests.exceptions.RequestException:
            return True
        except:
            return False

    # makes the Gtk thread execute the given callback.
    @staticmethod
    def add_mainloop_task(callback, *args):
        def cb(args):
            args[0](*args[1:])
            return False

        args = [callback] + list(args)
        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT, cb, args)

    @staticmethod
    def is_unity():
        return os.getenv("XDG_CURRENT_DESKTOP", "").lower() == "unity"

    @staticmethod
    def start_daemon(target):
        daemon_thread = threading.Thread(target=target)
        daemon_thread.daemon = True
        daemon_thread.start()
        return daemon_thread

    @staticmethod
    def check_variety_slideshow_present():
        return bool(shutil.which("variety-slideshow"))

    @staticmethod
    def convert_to_filename(url):
        url = re.sub(r"http://", "", url)
        url = re.sub(r"https://", "", url)
        valid_chars = "_%s%s" % (string.ascii_letters, string.digits)
        return "".join(c if c in valid_chars else "_" for c in url)

    @staticmethod
    def safe_unlink(filepath):
        try:
            os.unlink(filepath)
        except Exception:
            logger.exception(lambda: "Could not delete {}, ignoring".format(filepath))

    @staticmethod
    def copy_with_replace(from_path, to_path, search_replace_map):
        with open(from_path, "r") as file:
            data = file.read()
        for search, replace in search_replace_map.items():
            data = data.replace(search, replace)
        with open(to_path + ".partial", "w") as file:
            file.write(data)
            file.flush()
        os.rename(to_path + ".partial", to_path)

    @staticmethod
    def get_exec_path():
        return os.path.abspath(sys.argv[0])

    @staticmethod
    def get_folder_size(start_path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return total_size

    @staticmethod
    def get_screen_width():
        return Gdk.Screen.get_default().get_width()


def on_gtk(f):
    @functools.wraps(f)
    def wrapped(*args):
        Util.add_mainloop_task(f, *args)

    return wrapped


def safe_print(text, ascii_text=None, file=sys.stdout):
    """
    Python's print throws UnicodeEncodeError if the terminal encoding is borked. This version tries print, then logging, then printing the ascii text when one is present.
    If does not throw exceptions even if it fails.
    :param text: Text to print, str or unicode, possibly with non-ascii symbols in it
    :param ascii_text: optional. Original untranslated ascii version of the text when present.
    """
    try:
        print(text, file=file)
    except:  # UnicodeEncodeError can happen here if the terminal is strangely configured, but we are playing safe and catching everything
        try:
            logging.getLogger("variety").error(
                "Error printing non-ascii text, terminal encoding is %s" % sys.stdout.encoding
            )
            if ascii_text:
                try:
                    print(ascii_text)
                    return
                except:
                    pass
            logging.getLogger("variety").warning(text)
        except:
            pass
