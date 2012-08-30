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

import gettext
from gettext import gettext as _
import subprocess
from variety_lib.helpers import get_media_file
from variety.FacebookHelper import FacebookHelper

gettext.textdomain('variety')

from gi.repository import Gtk, Gdk, GdkPixbuf, GObject, Gio, Notify # pylint: disable=E0611
Notify.init("Variety")

from variety_lib import Window
from variety_lib import varietyconfig

import os
import stat
import shutil
import threading
import time
import logging
import random
import re

random.seed()
logger = logging.getLogger('variety')

from variety.AboutVarietyDialog import AboutVarietyDialog
from variety.PreferencesVarietyDialog import PreferencesVarietyDialog
from variety.FacebookFirstRunDialog import FacebookFirstRunDialog
from variety.FacebookPublishDialog import FacebookPublishDialog
from variety.DominantColors import DominantColors
from variety.WallpapersNetDownloader import WallpapersNetDownloader
from variety.WallbaseDownloader import WallbaseDownloader
from variety.DesktopprDownloader import DesktopprDownloader
from variety.APODDownloader import APODDownloader
from variety.FlickrDownloader import FlickrDownloader
from variety.Options import Options
from variety.ImageFetcher import ImageFetcher
from variety.Util import Util
from variety.ThumbsManager import ThumbsManager

MAX_FILES = 10000

# See variety_lib.Window.py for more details about how this class works
class VarietyWindow(Window):
    __gtype_name__ = "VarietyWindow"

    SCHEMA = 'org.gnome.desktop.background'
    KEY = 'picture-uri'

    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the main window"""
        super(VarietyWindow, self).finish_initializing(builder)

        self.gsettings = Gio.Settings.new(self.SCHEMA)

        self.AboutDialog = AboutVarietyDialog
        self.PreferencesDialog = PreferencesVarietyDialog
        self.thumbs_manager = ThumbsManager(self)

        self.prepare_config_folder()

        self.events = []

        self.create_downloaders_cache()

        self.prepared = []
        self.prepared_lock = threading.Lock()

        self.register_clipboard()

        # load config
        self.options = None
        self.load_banned()
        self.load_history()
        self.thumbs_manager.mark_active(file=self.used[self.position], position=self.position)
        self.reload_config()
        self.load_last_change_time()

        self.image_count = -1
        self.image_colors_cache = {}
        #TODO load image cache

        self.wheel_timer = None
        self.set_wp_timer = None

        self.update_indicator(auto_changed=False)
        self.auto_changed = True

        self.do_set_wp_lock = threading.Lock()
        self.start_threads()

        self.about = None
        self.preferences_dialog = None
        self.dialogs = []

    def prepare_config_folder(self):
        self.config_folder = os.path.expanduser("~/.config/variety")

        Util.makedirs(self.config_folder)

        shutil.copy(varietyconfig.get_data_file("config", "variety.conf"),
                    os.path.join(self.config_folder, "variety_latest_default.conf"))

        if not os.path.exists(os.path.join(self.config_folder, "variety.conf")):
            logger.info("Missing config file, copying it from " +
                        varietyconfig.get_data_file("config", "variety.conf"))
            shutil.copy(varietyconfig.get_data_file("config", "variety.conf"), self.config_folder)

        if not os.path.exists(os.path.join(self.config_folder, "ui.conf")):
            logger.info("Missing ui.conf file, copying it from " +
                        varietyconfig.get_data_file("config", "ui.conf"))
            shutil.copy(varietyconfig.get_data_file("config", "ui.conf"), self.config_folder)

        self.scripts_folder = os.path.join(self.config_folder, "scripts")
        if not os.path.exists(self.scripts_folder):
            logger.info("Missing scripts dir, copying it from " + varietyconfig.get_data_file("scripts"))
            shutil.copytree(varietyconfig.get_data_file("scripts"), self.scripts_folder)
        # make all scripts executable:
        for f in os.listdir(self.scripts_folder):
            path = os.path.join(self.scripts_folder, f)
            os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

    def register_clipboard(self):
        def clipboard_changed(clipboard, event):
            try:
                if not self.options.clipboard_enabled:
                    return

                text = clipboard.wait_for_text()
                logger.debug("Clipboard: %s" % text)
                if not text:
                    return

                valid = [url for url in text.split('\n') if
                         ImageFetcher.url_ok(url, self.options.clipboard_use_whitelist, self.options.clipboard_hosts)]

                if valid:
                    logger.info("Received clipboard URLs: " + str(valid))
                    self.process_urls(valid, verbose=False)
            except Exception:
                logger.exception("Exception when processing clipboard:")

        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.clipboard.connect("owner-change", clipboard_changed)

    def log_options(self):
        logger.info("Loaded options:")
        logger.info("Change on start: " + str(self.options.change_on_start))
        logger.info("Change enabled: " + str(self.options.change_enabled))
        logger.info("Change interval: " + str(self.options.change_interval))
        logger.info("Download enabled: " + str(self.options.download_enabled))
        logger.info("Download interval: " + str(self.options.download_interval))
        logger.info("Download folder: " + self.options.download_folder)
        logger.info("Quota enabled: " + str(self.options.quota_enabled))
        logger.info("Quota size: " + str(self.options.quota_size))
        logger.info("Favorites folder: " + self.options.favorites_folder)
        logger.info("Fetched folder: " + self.options.fetched_folder)
        logger.info("Clipboard enabled: " + str(self.options.clipboard_enabled))
        logger.info("Clipboard use whitelist: " + str(self.options.clipboard_use_whitelist))
        logger.info("Clipboard hosts: " + str(self.options.clipboard_hosts))
        logger.info("Color enabled: " + str(self.options.desired_color_enabled))
        logger.info("Color: " + (str(self.options.desired_color) if self.options.desired_color else "None"))
        logger.info("Min size enabled: " + str(self.options.min_size_enabled))
        logger.info("Min size: " + str(self.options.min_size))
        logger.info("Min width, height: %d %d" % (self.min_width, self.min_height))
        logger.info("Use landscape enabled: " + str(self.options.use_landscape_enabled))
        logger.info("Lightness enabled: " + str(self.options.lightness_enabled))
        logger.info("Lightness mode: " + str(self.options.lightness_mode))
        logger.info("Facebook enabled: " + str(self.options.facebook_enabled))
        logger.info("Facebook show dialog: " + str(self.options.facebook_show_dialog))
        logger.info("Images: " + str(self.individual_images))
        logger.info("Folders: " + str(self.folders))
        logger.info("All sources: " + str(self.options.sources))
        logger.info("Total downloaders: " + str(len(self.downloaders)))
        logger.info("Filters: " + str(self.filters))

    def reload_config(self):
        self.previous_options = self.options

        self.options = Options()
        self.options.read()

        Util.makedirs(self.options.download_folder)
        Util.makedirs(self.options.favorites_folder)
        Util.makedirs(self.options.fetched_folder)

        self.individual_images = [os.path.expanduser(s[2]) for s in self.options.sources if
                                  s[0] and s[1] == Options.SourceType.IMAGE]

        self.folders = [os.path.expanduser(s[2]) for s in self.options.sources if
                        s[0] and s[1] == Options.SourceType.FOLDER]

        if Options.SourceType.FAVORITES in [s[1] for s in self.options.sources if s[0]]:
            self.folders.append(self.options.favorites_folder)

        if Options.SourceType.FETCHED in [s[1] for s in self.options.sources if s[0]]:
            self.folders.append(self.options.fetched_folder)

        self.downloaders = []
        self.download_folder_size = -1

        if self.size_options_changed():
            logger.info("Size/landscape settings changed - purging downloaders cache")
            self.create_downloaders_cache()

        for s in self.options.sources:
            enabled, type, location = s

            if not enabled:
                continue
            if type not in Options.SourceType.dl_types:
                continue

            if location in self.downloaders_cache[type]:
                self.downloaders.append(self.downloaders_cache[type][location])
            else:
                try:
                    logger.info("Creating new downloader for type %d, location %s" % (type, location))
                    dlr = self.create_downloader(type, location)
                    self.downloaders_cache[type][location] = dlr
                    self.downloaders.append(dlr)
                except Exception:
                    logger.exception("Could not create Downloader for type %d, location %s" % (type, location))

        for downloader in self.downloaders:
            downloader.update_download_folder()
            Util.makedirs(downloader.target_folder)
            self.folders.append(downloader.target_folder)

        self.filters = [f[2] for f in self.options.filters if f[0]]

        self.min_width = 0
        self.min_height = 0
        if self.options.min_size_enabled:
            self.min_width = Gdk.Screen.get_default().get_width() * self.options.min_size // 100
            self.min_height = Gdk.Screen.get_default().get_height() * self.options.min_size // 100

        self.log_options()

        # clean prepared - they are outdated
        with self.prepared_lock:
            self.prepared = []
        self.image_count = -1

        GObject.idle_add(self.refresh_wallpaper)
        if self.events:
            for e in self.events:
                e.set()

    def size_options_changed(self):
        return self.previous_options and (
            self.previous_options.min_size_enabled != self.options.min_size_enabled or\
            self.previous_options.min_size != self.options.min_size or\
            self.options.use_landscape_enabled != self.options.use_landscape_enabled)

    def create_downloaders_cache(self):
        self.downloaders_cache = {}
        for type in Options.SourceType.dl_types:
            self.downloaders_cache[type] = {}

    def create_downloader(self, type, location):
        if type == Options.SourceType.DESKTOPPR:
            return DesktopprDownloader(self)
        elif type == Options.SourceType.APOD:
            return APODDownloader(self)
        elif type == Options.SourceType.WN:
            return WallpapersNetDownloader(self, location)
        elif type == Options.SourceType.FLICKR:
            return FlickrDownloader(self, location)
        elif type == Options.SourceType.WALLBASE:
            return WallbaseDownloader(self, location)
        else:
            raise Exception("Uknown downloader type")

    def get_folder_of_source(self, source):
        type = Options.str_to_type(source[1])
        location = source[2]

        if type == Options.SourceType.IMAGE:
            return None
        if type == Options.SourceType.FOLDER:
            return location
        elif type == Options.SourceType.FAVORITES:
            return self.options.favorites_folder
        elif type == Options.SourceType.FETCHED:
            return self.options.fetched_folder
        else:
            dlr = self.create_downloader(type, location)
            dlr.update_download_folder()
            return dlr.target_folder

    def load_banned(self):
        self.banned = set()
        try:
            with open(os.path.join(self.config_folder, "banned.txt")) as f:
                for line in f:
                    self.banned.add(line.strip())
        except Exception:
            logger.info("Missing or invalid banned URLs list, no URLs will be banned")

    def start_threads(self):
        self.running = True

        self.change_event = threading.Event()
        change_thread = threading.Thread(target=self.regular_change_thread)
        change_thread.daemon = True
        change_thread.start()

        self.prepare_event = threading.Event()
        prep_thread = threading.Thread(target=self.prepare_thread)
        prep_thread.daemon = True
        prep_thread.start()

        self.dl_event = threading.Event()
        dl_thread = threading.Thread(target=self.download_thread)
        dl_thread.daemon = True
        dl_thread.start()

        self.clock_event = threading.Event()
        clock_thread = threading.Thread(target=self.clock_thread)
        clock_thread.daemon = True
        clock_thread.start()

        self.events = [self.change_event, self.prepare_event, self.dl_event, self.clock_event]

    def is_in_favorites(self, file):
        filename = os.path.basename(file)
        return os.path.exists(os.path.join(self.options.favorites_folder, filename))

    def update_indicator(self, file=None, is_gtk_thread=True, auto_changed=None):
        if not file:
            file = self.current
        if auto_changed is None:
            auto_changed = self.auto_changed

        logger.info("Setting file info to: " + str(file))
        try:
            self.url = None
            self.image_url = None
            self.source_name = None

            label = os.path.dirname(file).replace('_', '__')
            info = Util.read_metadata(file)
            if info and "sourceURL" in info and "sourceName" in info:
                self.source_name = info["sourceName"] if info["sourceName"].find("Fetched") < 0 else None
                label = "View at " + info["sourceName"] if info["sourceName"].find("Fetched") < 0 else "Fetched: Show Origin"
                self.url = info["sourceURL"]
                if "imageURL" in info:
                    self.image_url = info["imageURL"]
            if len(label) > 50:
                label = label[:50] + "..."

            trash_enabled = os.access(file, os.W_OK)
            in_favs = self.is_in_favorites(file)

            if not is_gtk_thread:
                Gdk.threads_enter()

            for i in xrange(10):
                self.ind.prev.set_sensitive(self.position < len(self.used) - 1)
                self.ind.file_label.set_label(os.path.basename(file).replace('_', '__'))

                if auto_changed:
                    # delay enabling Move/Copy operations in this case - see comment below
                    self.ind.trash.set_sensitive(False)
                    self.ind.favorite.set_sensitive(False)
                else:
                    self.ind.trash.set_sensitive(trash_enabled)
                    self.ind.favorite.set_sensitive(not in_favs)

                self.ind.favorite.set_label("Already in Favorites" if in_favs else "Copy to _Favorites")

                self.ind.show_origin.set_label(label)
                self.ind.show_origin.set_sensitive(True)

                if self.thumbs_manager.thumbs_window and self.thumbs_manager.type == "history":
                    self.ind.history.set_label("Close _History")
                else:
                    self.ind.history.set_label("Show _History")

                fb_enabled = self.options.facebook_enabled and (self.url is not None)
                self.ind.publish_fb.set_visible(fb_enabled)

                self.update_pause_resume()

            if not is_gtk_thread:
                Gdk.threads_leave()

            # delay enabling Move/Copy operations after automatic changes - protect from inadvertent clicks
            if auto_changed:
                def update_file_operations():
                    Gdk.threads_enter()
                    for i in xrange(10):
                        self.ind.trash.set_sensitive(trash_enabled)
                        self.ind.favorite.set_sensitive(not in_favs)
                    Gdk.threads_leave()
                enable_timer = threading.Timer(2, update_file_operations)
                enable_timer.start()

        except Exception:
            logger.exception("Error updating file info")

    def update_pause_resume(self):
        self.ind.pause_resume.set_label("Pause" if self.options.change_enabled else "Resume")

    def regular_change_thread(self):
        logger.info("regular_change thread running")

        if self.options.change_on_start:
            self.change_event.wait(5) # wait for prepare thread to prepare some images first
            self.auto_changed = True
            self.change_wallpaper()

        while self.running:
            try:
                while not self.options.change_enabled or \
                      (time.time() - self.last_change_time) < self.options.change_interval:
                    if not self.running:
                        return
                    now = time.time()
                    wait_more = self.options.change_interval - (now - self.last_change_time)
                    if self.options.change_enabled:
                        self.change_event.wait(max(0, wait_more))
                    else:
                        logger.info("regular_change: waiting till user resumes")
                        self.change_event.wait()
                    self.change_event.clear()
                if not self.running:
                    return
                if not self.options.change_enabled:
                    continue
                logger.info("regular_change changes wallpaper")
                self.auto_changed = True
                self.last_change_time = time.time()
                self.change_wallpaper()
            except Exception:
                logger.exception("Exception in regular_change_thread")

    def clock_thread(self):
        logger.info("clock thread running")

        last_minute = -1
        while self.running:
            try:
                while not self.options.clock_enabled:
                    self.clock_event.wait()
                    self.clock_event.clear()

                if not self.running:
                    return
                if not self.options.clock_enabled:
                    continue

                time.sleep(1)
                minute = int(time.strftime("%M", time.localtime()))
                if minute != last_minute:
                    logger.info("clock_thread updates wallpaper")
                    self.auto_changed = False
                    self.refresh_clock()
                    last_minute = minute
            except Exception:
                logger.exception("Exception in clock_thread")

    def prepare_thread(self):
        logger.info("prepare thread running")
        while self.running:
            try:
                logger.info("prepared buffer contains %s images" % len(self.prepared))

                if self.image_count < 0 or len(self.prepared) <= min(10, self.image_count // 2):
                    logger.info("preparing some images")
                    images = self.select_random_images(100)

                    found = set()
                    for fuzziness in xrange(0, 5):
                        if len(found) > 10 or len(found) >= len(images):
                            break
                        for img in images:
                            try:
                                if self.image_ok(img, fuzziness):
                                    if not img in found:
                                        found.add(img)
                                        if self.options.desired_color_enabled or self.options.use_landscape_enabled or\
                                           self.options.min_size_enabled or self.options.lightness_enabled:
                                            logger.debug("ok at fuzziness %s: %s" % (str(fuzziness), img))
                            except Exception:
                                logger.exception("Excepion while testing image_ok on file " + img)

                    with self.prepared_lock:
                        self.prepared.extend(found)
                        if not self.prepared and images:
                            logger.info("Prepared buffer still empty after search, appending some non-ok image")
                            self.prepared.append(images[random.randint(0, len(images) - 1)])

                        # remove duplicates
                        self.prepared = list(set(self.prepared))
                        random.shuffle(self.prepared)

                    logger.info("after search prepared buffer contains %s images" % len(self.prepared))
            except Exception:
                logger.exception("Error in prepare thread:")

            self.prepare_event.wait(30)
            self.prepare_event.clear()

    def download_thread(self):
        while self.running:
            try:
                self.dl_event.wait(self.options.download_interval)
                self.dl_event.clear()
                if not self.running:
                    return
                if not self.options.download_enabled:
                    continue
                    #TODO do we want to download when not change_enabled?
                if self.downloaders:
                    self.purge_downloaded()
                if self.downloaders:
                    downloader = self.downloaders[random.randint(0, len(self.downloaders) - 1)]
                    file = downloader.download_one()
                    if file:
                        self.download_folder_size += os.path.getsize(file)
                        if self.image_ok(file, 0):
                            pos = random.randint(0, 0) #TODO how much priority do we want to give it?
                            logger.info("Adding downloaded file %s near queue front at position %d" % (file, pos))
                            with self.prepared_lock:
                                self.prepared.insert(pos, file) # give priority to newly-downloaded images
                        else:
                            self.prepare_event.set()
            except Exception:
                logger.exception("Could not download wallpaper:")

    def purge_downloaded(self):
        if not self.options.quota_enabled:
            return

        if self.download_folder_size <= 0 or random.randint(0, 20) == 0:
            self.download_folder_size = self.get_folder_size(self.options.download_folder)
            logger.info("Refreshed download folder size: %d mb", self.download_folder_size / (1024.0 * 1024.0))

        mb_quota = self.options.quota_size * 1024 * 1024
        if self.download_folder_size > 0.95 * mb_quota:
            logger.info("Purging oldest files from download folder, current size: %d mb" %
                        int(self.download_folder_size / (1024.0 * 1024.0)))
            files = []
            for dirpath, dirnames, filenames in os.walk(self.options.download_folder):
                for f in filenames:
                    if Util.is_image(f):
                        fp = os.path.join(dirpath, f)
                        files.append((fp, os.path.getsize(fp), os.path.getctime(fp)))
            files = sorted(files, key=lambda x: x[2])
            i = 0
            while i < len(files) and self.download_folder_size > 0.80 * mb_quota:
                file = files[i][0]
                if file != self.current:
                    try:
                        logger.debug("Deleting old file in downloaded: " + file)
                        self.remove_from_queues(file)
                        os.unlink(file)
                        self.download_folder_size -= files[i][1]
                        try:
                            os.unlink(file + ".txt")
                        except Exception:
                            pass
                    except Exception:
                        logger.exception("Could not delete some file while purging download folder: " + file)
                i += 1

    @staticmethod
    def get_folder_size(start_path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    def set_wp_throttled(self, filename, delay=0.3):
        self.thumbs_manager.mark_active(file=self.used[self.position], position=self.position)
        if self.set_wp_timer:
            self.set_wp_timer.cancel()
        def _do_set_wp(): self.do_set_wp(filename)
        self.set_wp_timer = threading.Timer(delay, _do_set_wp)
        self.set_wp_timer.start()

    def build_imagemagick_filter_cmd(self, filename):
        if not self.filters:
            return None

        w = Gdk.Screen.get_default().get_width()
        h = Gdk.Screen.get_default().get_height()
        cmd = 'convert "%s" -scale %dx%d^ ' % (filename, w, h)

        filter = self.filters[random.randint(0, len(self.filters) - 1)]
        if filter.strip():
            logger.info("Applying filter: " + filter)
            cmd += filter + ' '

        cmd = cmd + ' "' + os.path.join(self.config_folder, "wallpaper-filter.jpg") + '"'
        logger.info("ImageMagick filter cmd: " + cmd)
        return cmd

    def build_imagemagick_clock_cmd(self, filename):
        if not self.options.clock_enabled:
            return None

        w = Gdk.Screen.get_default().get_width()
        h = Gdk.Screen.get_default().get_height()
        cmd = 'convert "%s" -scale %dx%d^ ' % (filename, w, h)

        if self.options.clock_enabled and self.options.clock_filter.strip():
            hoffset, voffset = VarietyWindow.compute_clock_offsets(filename, w, h)
            clock_filter = self.options.clock_filter
            clock_filter = VarietyWindow.replace_clock_filter_offsets(clock_filter, hoffset, voffset)
            clock_filter = time.strftime(clock_filter, time.localtime())

            logger.info("Applying clock filter: " + clock_filter)
            cmd += clock_filter + ' '

        cmd = cmd + ' "' + os.path.join(self.config_folder, "wallpaper-clock.jpg") + '"'
        logger.info("ImageMagick clock cmd: " + cmd)
        return cmd

    @staticmethod
    def compute_clock_offsets(filename, screen_w, screen_h):
        screen_ratio = float(screen_w) / screen_h
        iw, ih = Util.get_size(filename)
        hoffset = voffset = 0
        if screen_ratio > float(iw) / ih: #image is "taller" than the screen ratio - need to offset vertically
            scaledw = float(screen_w)
            scaledh = ih * scaledw / iw
            voffset = int((scaledh - float(scaledw) / screen_ratio) / 2)
        else: #image is "wider" than the screen ratio - need to offset horizontally
            scaledh = float(screen_h)
            scaledw = iw * scaledh / ih
            hoffset = int((scaledw - float(scaledh) * screen_ratio) / 2)
        logger.info("Clock filter debug info: w:%d, h:%d, ratio:%f, iw:%d, ih:%d, scw:%d, sch:%d, ho:%d, vo:%d" % (
            screen_w, screen_h, screen_ratio, iw, ih, scaledw, scaledh, hoffset, voffset))
        return hoffset, voffset

    @staticmethod
    def replace_clock_filter_offsets(filter, hoffset, voffset):
        def hrepl(m): return str(hoffset + int(m.group(1)))
        def vrepl(m): return str(voffset + int(m.group(1)))
        filter = re.sub(r"\[\%HOFFSET\+(\d+)\]", hrepl, filter)
        filter = re.sub(r"\[\%VOFFSET\+(\d+)\]", vrepl, filter)
        return filter


    class RefreshLevel:
        ALL = 0
        FILTERS_AND_CLOCK = 1
        CLOCK_ONLY = 2

    def refresh_wallpaper(self):
        self.do_set_wp(self.current, refresh_level=VarietyWindow.RefreshLevel.FILTERS_AND_CLOCK)

    def refresh_clock(self):
        self.do_set_wp(self.current, refresh_level=VarietyWindow.RefreshLevel.CLOCK_ONLY)

    def write_filtered_wallpaper_origin(self, filename):
        try:
            with open(os.path.join(self.config_folder, "wallpaper.jpg.txt"), "w") as f:
                f.write(filename)
        except Exception:
            pass

    def do_set_wp(self, filename, refresh_level=RefreshLevel.ALL):
        with self.do_set_wp_lock:
            self.set_wp_timer = None

            try:
                if not os.access(filename, os.R_OK):
                    logger.info("Missing file or bad permissions, will not use it: " + filename)
                    return

                to_set = filename
                if self.filters:
                    if refresh_level != VarietyWindow.RefreshLevel.CLOCK_ONLY:
                        self.post_filter_filename = to_set
                        cmd = self.build_imagemagick_filter_cmd(filename)
                        result = os.system(cmd)
                        if result == 0: #success
                            to_set = os.path.join(self.config_folder, "wallpaper-filter.jpg")
                            self.post_filter_filename = to_set
                            self.write_filtered_wallpaper_origin(filename)
                        else:
                            logger.warning("Could not execute filter convert command - missing ImageMagick or bad filter defined?")
                    else:
                        to_set = self.post_filter_filename

                if self.options.clock_enabled:
                    cmd = self.build_imagemagick_clock_cmd(to_set)
                    result = os.system(cmd)
                    if result == 0: #success
                        to_set = os.path.join(self.config_folder, "wallpaper-clock.jpg")
                        self.write_filtered_wallpaper_origin(filename)
                    else:
                        logger.warning("Could not execute clock convert command - missing ImageMagick or bad filter defined?")

                self.update_indicator(filename, False)
                self.set_desktop_wallpaper(to_set)
                self.current = filename

                if refresh_level == VarietyWindow.RefreshLevel.ALL:
                    self.last_change_time = time.time()
                    self.save_last_change_time()
                    self.save_history()
            except Exception:
                logger.exception("Error while setting wallpaper")

    def list_images(self):
        return Util.list_files(self.individual_images, self.folders, Util.is_image, MAX_FILES)

    def select_random_images(self, count):
        # refresh image count often when few images in the folders and rarely when many:
        if self.image_count < 20 or random.randint(0, max(0, min(100, self.image_count // 30))) == 0:
            cnt = sum(1 for f in self.list_images())
            if not cnt:
                return []

            self.image_count = cnt
            logger.info("Refreshed image count: %d" % self.image_count)
        else:
            cnt = self.image_count

        indexes = set()
        for i in xrange(count):
            indexes.add(random.randint(0, cnt - 1))

        result = []
        for index, f in enumerate(self.list_images()):
            if index in indexes:
                result.append(f)
                indexes.remove(index)
                if not indexes:
                    break

        random.shuffle(result)
        return result

    def on_indicator_scroll(self, indicator, steps, direction):
        if self.wheel_timer:
            self.wheel_timer.cancel()
        self.wheel_direction = direction
        self.wheel_timer = threading.Timer(0.3, self.handle_scroll)
        self.wheel_timer.start()

    def handle_scroll(self):
        if self.wheel_direction:
            self.next_wallpaper(widget=self)
        else:
            self.prev_wallpaper(widget=self)
        self.wheel_timer = None

    def prev_wallpaper(self, widget=None):
        self.auto_changed = widget is None
        if self.position >= len(self.used) - 1:
            return
        else:
            self.position += 1
            self.set_wp_throttled(self.used[self.position])

    def next_wallpaper(self, widget=None, bypass_history=False):
        self.auto_changed = widget is None
        if self.position > 0 and not bypass_history:
            self.position -= 1
            self.set_wp_throttled(self.used[self.position])
        else:
            if bypass_history:
                self.position = 0
            self.change_wallpaper()

    def move_to_history_position(self, position):
        if 0 <= position < len(self.used):
            self.auto_changed = False
            self.position = position
            self.set_wp_throttled(self.used[self.position])
        else:
            logger.warning("Invalid position passed to move_to_history_position, %d, used len is %d" % (position, len(self.used)))

    def show_notification(self, title, message="", icon=None):
        if not icon:
            icon = get_media_file("variety.svg")
        try:
            self.notification.update(title, message, icon)
        except AttributeError:
            self.notification = Notify.Notification.new(title, message, icon)
        self.notification.set_urgency(Notify.Urgency.LOW)
        self.notification.show()

    def change_wallpaper(self, widget=None):
        try:
            img = None

            with self.prepared_lock:
                for prep in self.prepared:
                    if prep != self.current and os.access(prep, os.R_OK):
                        img = prep
                        self.prepared.remove(img)
                        self.prepare_event.set()
                        break

            if not img:
                logger.info("No images yet in prepared buffer, using some random image")
                rnd_images = self.select_random_images(10)
                rnd_images = [f for f in rnd_images if f != self.current]
                img = rnd_images[0] if rnd_images else None

            if not img:
                logger.info("No images found")
                if not self.auto_changed:
                    self.show_notification(
                        "No more wallpapers",
                        "Please add more image sources or wait for some downloads")
                return

            self.set_wallpaper(img, auto_changed=self.auto_changed)
        except Exception:
            logger.exception("Could not change wallpaper")

    def set_wallpaper(self, img, throttle=True, auto_changed=False):
        if img == self.current:
            return
        if os.access(img, os.R_OK):
            at_front = self.position == 0
            self.used = self.used[self.position:]
            self.used.insert(0, img)

            self.refresh_thumbs_history(img, at_front)

            self.position = 0
            if len(self.used) > 1000:
                self.used = self.used[:1000]
            self.auto_changed = auto_changed
            self.last_change_time = time.time()
            if throttle:
                self.set_wp_throttled(img)
            else:
                self.set_wp_throttled(img, 0)

    def refresh_thumbs_history(self, added_image, at_front=False):
        if self.thumbs_manager.is_showing("history"):
            def _add():
                if at_front:
                    self.thumbs_manager.add_image(added_image, gdk_thread=False)
                else:
                    self.thumbs_manager.show(self.used[:200], gdk_thread=False, type="history")
                    self.thumbs_manager.pin()
            add_timer = threading.Timer(0, _add)
            add_timer.start()

    def image_ok(self, img, fuzziness):
        try:
            if not self.options.desired_color_enabled and not self.options.lightness_enabled:
                if not self.options.use_landscape_enabled and not self.options.min_size_enabled:
                    return True
                else:
                    if img in self.image_colors_cache:
                        width = self.image_colors_cache[img][3]
                        height = self.image_colors_cache[img][4]
                    else:
                        dom = DominantColors(img)
                        width = dom.get_width()
                        height = dom.get_height()

                    return self.size_ok(width, height, fuzziness)
            else:
                if not img in self.image_colors_cache:
                    dom = DominantColors(img, False)
                    self.image_colors_cache[img] = dom.get_dominant_colors()
                colors = self.image_colors_cache[img]

                ok = self.size_ok(colors[3], colors[4], fuzziness)

                if self.options.lightness_enabled:
                    lightness = colors[2]
                    if self.options.lightness_mode == Options.LightnessMode.DARK:
                        ok = ok and lightness < 75 + fuzziness * 6
                    elif self.options.lightness_mode == Options.LightnessMode.LIGHT:
                        ok = ok and lightness > 180 - fuzziness * 6
                    else:
                        logger.warning("Unknown lightness mode: %d", self.options.lightness_mode)

                if self.options.desired_color_enabled and self.options.desired_color:
                    ok = ok and DominantColors.contains_color(colors, self.options.desired_color, fuzziness + 2)

                return ok
        except Exception, err:
            logger.exception("Error in image_ok:")
            return False

    def size_ok(self, width, height, fuzziness=0):
        ok = True

        if self.options.min_size_enabled:
            ok = ok and width >= self.min_width - fuzziness * 100
            ok = ok and height >= self.min_height - fuzziness * 70

        if self.options.use_landscape_enabled:
            ok = ok and width > height

        return ok

    def open_folder(self, widget=None, file=None):
        if not file:
            file = self.current
        os.system("xdg-open \"" + os.path.dirname(file) + "\"")

    def open_file(self, widget=None, file=None):
        if not file:
            file = self.current
        os.system("xdg-open \"" + os.path.realpath(file) + "\"")

    def on_show_origin(self, widget=None):
        if self.url:
            os.system("xdg-open " + self.url)
        else:
            self.open_folder()

    def confirm_move(self, move_or_copy, file, to):
        dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
            Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO,
            move_or_copy + " " + os.path.basename(file) + " to " + to + ". Are you sure?")
        dialog.set_title("Confirm " + move_or_copy + " to " + to)
        self.dialogs.append(dialog)
        response = dialog.run()
        dialog.destroy()
        self.dialogs.remove(dialog)
        return response == Gtk.ResponseType.YES

    def move_or_copy_file(self, file, to, to_name, operation):
        op = "Moved" if operation == shutil.move else "Copied"
        try:
            operation(file, to)
            try:
                operation(file + ".txt", to)
            except Exception:
                pass
            logger.info(op + " " + file + " to " + to)
            #self.show_notification(op, op + " " + os.path.basename(file) + " to " + to_name)
            return True
        except Exception as err:
            success = False

            if str(err).find("already exists") > 0:
                if operation == shutil.move:
                    try:
                        os.unlink(file)
                        success = True
                        #self.show_notification(op, op + " " + os.path.basename(file) + " to " + to_name)
                    except Exception:
                        pass
                else:
                    success = True

            if not success:
                logger.exception("Could not move/copy to " + to)
                op = ("Move" if operation == shutil.move else "Copy")
                dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
                    Gtk.MessageType.WARNING, Gtk.ButtonsType.OK,
                    "Could not " + op.lower() + " to " + to + ". You probably don't have permissions to " + op.lower() + " this file.")
                self.dialogs.append(dialog)
                dialog.set_title(op + " failed")
                dialog.run()
                dialog.destroy()
                self.dialogs.remove(dialog)
                return False

    def move_to_trash(self, widget=None, file=None):
        try:
            if not file:
                file = self.current
            url = self.url
            if not os.access(file, os.W_OK):
                self.show_notification("Cannot move", "You don't have permissions to move %s to Trash." % file)
            else:
                trash = os.path.expanduser("~/.local/share/Trash")
                self.move_or_copy_file(file, trash, "trash", shutil.move)
                if self.current == file:
                    self.next_wallpaper(widget)

                self.remove_from_queues(file)
                if url:
                    self.ban_url(url)

                self.thumbs_manager.remove_image(file)
        except Exception:
            logger.exception("Exception in move_to_trash")

    def ban_url(self, url):
        try:
            self.banned.add(url)
            with open(os.path.join(self.config_folder, "banned.txt"), "a") as f:
                f.write(self.url + "\n")
        except Exception:
            logger.exception("Could not ban URL")

    def remove_from_queues(self, file):
        self.used = [f for f in self.used if f != file]
        with self.prepared_lock:
            self.prepared = [f for f in self.prepared if f != file]

    def copy_to_favorites(self, widget=None, file=None):
        try:
            if not file:
                file = self.current
            if os.access(file, os.R_OK):
                self.move_or_copy_file(file, self.options.favorites_folder, "favorites", shutil.copy)
                self.update_indicator(auto_changed=False)
        except Exception:
            logger.exception("Exception in copy_to_favorites")

    def on_quit(self, widget=None):
        logger.info("Quitting")
        if self.running:
            for d in self.dialogs + [self.preferences_dialog, self.about]:
                try:
                    if d:
                        d.destroy()
                except Exception:
                    logger.exception("Could not destroy dialog")
                    pass

            self.running = False
            for e in self.events:
                e.set()

            if self.options.clock_enabled:
                self.options.clock_enabled = False
                GObject.idle_add(self.refresh_clock)

            Util.start_force_exit_thread(15)
            GObject.idle_add(Gtk.main_quit)

    def first_run(self):
        fr_file = os.path.join(self.config_folder, ".firstrun")
        if not os.path.exists(fr_file):
            f = open(fr_file, "w")
            f.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            f.close()
            self.show()

    def on_continue_clicked(self, button=None):
        self.destroy()
        self.on_mnu_preferences_activate(button)

    def edit_prefs_file(self, widget=None):
        dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.DESTGROY_WITH_PARENT,
            Gtk.MessageType.INFO, Gtk.ButtonsType.OK,
            "I will open an editor with the config file and apply the changes after you save and close the editor.")
        self.dialogs.append(dialog)
        dialog.set_title("Edit config file")
        dialog.run()
        dialog.destroy()
        self.dialogs.remove(dialog)
        os.system("gedit ~/.config/variety/variety.conf")
        self.reload_config()

    def on_pause_resume(self, widget=None):
        self.options.change_enabled = not self.options.change_enabled
        self.options.write()
        self.update_indicator(auto_changed=False)
        self.change_event.set()

    def process_urls(self, urls, verbose=True):
        def fetch():
            try:
                Util.makedirs(self.options.fetched_folder)

                for url in urls:
                    if not self.running:
                        return

                    is_local = os.path.exists(url)

                    if is_local:
                        if not (os.path.isfile(url) and Util.is_image(url)):
                            self.show_notification("Not an image", url)
                            continue

                        file = url
                        local_name = os.path.basename(file)
                        self.show_notification("Added to queue", "%s\nPress Next to see it" % local_name, icon=file)
                    else:
                        file = ImageFetcher.fetch(self, url, self.options.fetched_folder, verbose)

                    if file:
                        with self.prepared_lock:
                            logger.info("Adding fetched file %s to used queue immediately after current file" % file)

                            self.prepared.insert(0, file)
                            if self.used[self.position] != file and (self.position <= 0 or self.used[self.position - 1] != file):
                                at_front = self.position == 0
                                self.used.insert(self.position, file)
                                self.position += 1
                                self.refresh_thumbs_history(file, at_front)

            except Exception:
                logger.exception("Exception in process_urls")

        fetch_thread = threading.Thread(target=fetch)
        fetch_thread.daemon = True
        fetch_thread.start()

    def get_desktop_wallpaper(self):
        try:
            script = os.path.join(self.scripts_folder, "get_wallpaper")

            file = None

            if os.access(script, os.X_OK):
                logger.debug("Running get_wallpaper script")
                try:
                    output = subprocess.check_output(script).strip()
                    if output:
                        file = output
                except subprocess.CalledProcessError:
                    logger.exception("Exception when calling get_wallpaper script")
            else:
                logger.warning("get_wallpaper script is missing or not executable: " + script)

            if not file:
                file = self.gsettings.get_string(self.KEY)

            if not file:
                return None

            if file[0] == file[-1] == "'" or file[0] == file[-1] == '"':
                file = file[1:-1]

            file = file.replace("file://", "")
            return file
        except Exception:
            logger.exception("Could not get current wallpaper")
            return None

    def set_desktop_wallpaper(self, wallpaper):
        script = os.path.join(self.scripts_folder, "set_wallpaper")
        if os.access(script, os.X_OK):
            auto = "auto" if self.auto_changed else "manual"
            logger.debug("Running set_wallpaper script with parameters: %s, %s" % (wallpaper, auto))
            try:
                subprocess.check_call([script, wallpaper, auto])
                return
            except subprocess.CalledProcessError:
                logger.exception("Exception when calling set_wallpaper script")
        else:
            logger.warning("set_wallpaper script is missing or not executable: " + script)

        self.gsettings.set_string(self.KEY, "file://" + wallpaper)
        self.gsettings.apply()

    def show_hide_history(self, widget=None):
        if self.thumbs_manager.is_showing("history"):
            self.thumbs_manager.hide(gdk_thread=True, force=True)
        else:
            self.thumbs_manager.show(self.used[:200], gdk_thread=True, type="history")
            self.thumbs_manager.pin()
        self.update_indicator(auto_changed=False)

    def save_last_change_time(self):
        with open(os.path.join(self.config_folder, ".last_change_time"), "w") as f:
            f.write(str(self.last_change_time))

    def load_last_change_time(self):
        now = time.time()
        self.last_change_time = now

        # take persisted last_change_time into consideration only if the change interval is more than 6 hours:
        # thus users who change often won't have the wallpaper changed practically on every start,
        # and users who change rarely will still have their wallpaper changed sometimes even if Variety or the computer
        # does not run all the time
        if self.options.change_interval >= 6 * 60 * 60:
            try:
                with open(os.path.join(self.config_folder, ".last_change_time")) as f:
                    self.last_change_time = float(f.read().strip())
                    if self.last_change_time > now:
                        logger.warning("Persisted last_change_time after current time, setting to current time")
                        self.last_change_time = now
                logger.info("Change interval >= 6 hours, using persisted last_change_time " + str(self.last_change_time))
                logger.info("Still to wait: %d seconds" % max(0, self.options.change_interval - (time.time() - self.last_change_time)))
            except Exception:
                logger.info("Could not read last change time, setting it to current time")
                self.last_change_time = now
        else:
            logger.info("Change interval < 6 hours, ignore persisted last_change_time, " \
                        "wait initially the whole interval: " + str(self.options.change_interval))


    def save_history(self):
        try:
            start = max(0, self.position - 100) # TODO do we want to remember forward history?
            end = min(self.position + 100, len(self.used))
            to_save = self.used[start:end]
            with open(os.path.join(self.config_folder, "history.txt"), "w") as f:
                f.write("%d\n" % (self.position - start))
                for file in to_save:
                    f.write(file + "\n")
        except Exception:
            logger.exception("Could not save history")

    def load_history(self):
        self.used = []
        self.position = 0

        try:
            with open(os.path.join(self.config_folder, "history.txt"), "r") as f:
                lines = list(f)
            self.position = int(lines[0].strip())
            for i, line in enumerate(lines[1:]):
                if os.access(line.strip(), os.R_OK):
                    self.used.append(line.strip())
                elif i <= self.position:
                    self.position = max(0, self.position - 1)
        except Exception:
            logger.warning("Could not load history file, continuing without it, no worries")

        current = self.get_desktop_wallpaper()
        if current:
            if os.path.normpath(os.path.dirname(current)) == os.path.normpath(self.config_folder):
                try:
                    with open(os.path.join(self.config_folder, "wallpaper.jpg.txt")) as f:
                        current = f.read().strip()
                except Exception:
                    pass

        self.current = current
        if self.current and (self.position >= len(self.used) or current != self.used[self.position]):
            self.used.insert(0, self.current)
            self.position = 0

    def publish_on_facebook(self, widget):
        if not self.url:
            logger.warning("publish_on_facebook called with no current URL")
            return

        file = self.current
        link = self.url
        picture = self.image_url
        caption = None
        if self.source_name:
            caption = self.source_name + ", via Variety Wallpaper Changer"
        logger.info("Publish on FB requested with params %s, %s, %s" % (link, picture, caption))

        first_run_file = os.path.join(self.config_folder, ".fbfirstrun")
        if not os.path.exists(first_run_file):
            if hasattr(self, "facebook_dialog") and self.facebook_dialog:
                self.facebook_dialog.present()
                return
            else:
                self.facebook_dialog = FacebookFirstRunDialog()
                self.dialogs.append(self.facebook_dialog)
                self.facebook_dialog.run()
                if not self.running:
                    return
                with open(first_run_file, "w") as f:
                    f.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

        if hasattr(self, "facebook_dialog") and self.facebook_dialog:
            self.facebook_dialog.destroy()
            try:
                self.dialogs.remove(self.facebook_dialog)
            except Exception:
                pass

        self.facebook_dialog = None
        publish = True

        if self.options.facebook_show_dialog:
            self.facebook_dialog = FacebookPublishDialog()
            self.dialogs.append(self.facebook_dialog)
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file, 200, 100)
            self.facebook_dialog.ui.image.set_from_pixbuf(pixbuf)
            buf = self.facebook_dialog.ui.message.get_buffer()
            buf.set_text(self.options.facebook_message)
            response = self.facebook_dialog.run()
            if not self.running:
                return
            if response != Gtk.ResponseType.OK:
                publish = False
            else:
                self.options.facebook_message = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip()
                self.options.facebook_show_dialog = not self.facebook_dialog.ui.hide_dialog.get_active()
                self.options.write()

        try:
            if self.facebook_dialog:
                self.dialogs.remove(self.facebook_dialog)
        except Exception:
            pass

        if publish:
            def do_publish():
                fb = FacebookHelper(token_file=os.path.join(self.config_folder, ".fbtoken"))
                def on_success(fb, action, data):
                    self.show_notification("Published", "You may open your Facebook feed to see the post", icon=file)
                def on_failure(fb, action, data):
                    self.show_notification("Could not publish", str(data), icon=file)

                fb.publish(message=self.options.facebook_message, link=link, picture=picture, caption=caption,
                    on_success=on_success, on_failure=on_failure)
            GObject.idle_add(do_publish)
