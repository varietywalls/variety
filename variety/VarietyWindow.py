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

gettext.textdomain('variety')

from gi.repository import Gtk, Gdk, Gio # pylint: disable=E0611

from variety_lib import Window
from variety_lib import varietyconfig
from variety.AboutVarietyDialog import AboutVarietyDialog
from variety.PreferencesVarietyDialog import PreferencesVarietyDialog

import os
import shutil
import threading
import time

import logging

logger = logging.getLogger('variety')

import random

random.seed()

from variety.DominantColors import DominantColors
from variety.WallpapersNetDownloader import WallpapersNetDownloader
from variety.DesktopprDownloader import DesktopprDownloader
from variety.FlickrDownloader import FlickrDownloader
from variety.Options import Options

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

        self.prepare_config_folder()

        self.events = []

        self.wn_downloaders_cache = {}
        self.flickr_downloaders_cache = {}

        self.prepared = []
        self.prepared_lock = threading.Lock()

        # load config
        self.reload_config()
        self.load_banned()

        current = self.gsettings.get_string(self.KEY).replace("file://", "")
        if os.path.normpath(current) == os.path.normpath(os.path.join(self.config_folder, "wallpaper.jpg")):
            try:
                with open(os.path.join(self.config_folder, "wallpaper.jpg.txt")) as f:
                    current = f.read().strip()
            except Exception:
                pass

        self.used = [current, ]
        self.position = 0
        self.current = self.used[self.position]

        self.last_change_time = 0

        self.image_count = -1
        self.image_colors_cache = {}
        #TODO load image cache

        self.wheel_timer = None
        self.set_wp_timer = None

        self.update_indicator(self.current, False)

        self.start_threads()

        self.about = None
        self.preferences_dialog = None
        self.dialogs = []

    def prepare_config_folder(self):
        self.config_folder = os.path.expanduser("~/.config/variety")

        if not os.path.exists(os.path.join(self.config_folder, "variety.conf")):
            logger.info("Missing config file, copying it from " +
                        varietyconfig.get_data_file("config", "variety.conf"))
            shutil.copy(varietyconfig.get_data_file("config", "variety.conf"), self.config_folder)

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
        logger.info("Color enabled: " + str(self.options.desired_color_enabled))
        logger.info("Color: " + (str(self.options.desired_color) if self.options.desired_color else "None"))
        logger.info("Min size enabled: " + str(self.options.min_size_enabled))
        logger.info("Min size: " + str(self.options.min_size))
        logger.info("Min width, height: %d %d" % (self.min_width, self.min_height))
        logger.info("Use landscape enabled: " + str(self.options.use_landscape_enabled))
        logger.info("Lightness enabled: " + str(self.options.lightness_enabled))
        logger.info("Lightness mode: " + str(self.options.lightness_mode))
        logger.info("Images: " + str(self.individual_images))
        logger.info("Folders: " + str(self.folders))
        logger.info("WN URLs: " + str(self.wallpaper_net_urls))
        logger.info("Flickr searches: " + str(self.flickr_searches))
        logger.info("Total downloaders: " + str(len(self.downloaders)))
        logger.info("Filters: " + str(self.filters))

    def reload_config(self):
        self.options = Options()
        self.options.read()

        try:
            os.makedirs(self.options.download_folder)
        except OSError:
            pass
        try:
            os.makedirs(self.options.favorites_folder)
        except OSError:
            pass

        self.individual_images = [os.path.expanduser(s[2]) for s in self.options.sources if
                                  s[0] and s[1] == Options.SourceType.IMAGE]

        self.folders = [os.path.expanduser(s[2]) for s in self.options.sources if
                        s[0] and s[1] == Options.SourceType.FOLDER]

        if Options.SourceType.FAVORITES in [s[1] for s in self.options.sources if s[0]]:
            self.folders.append(self.options.favorites_folder)

        self.downloaders = []
        self.download_folder_size = -1

        if Options.SourceType.DESKTOPPR in [s[1] for s in self.options.sources if s[0]]:
            self.downloaders.append(DesktopprDownloader(self))

        self.wallpaper_net_urls = [s[2] for s in self.options.sources if s[0] and s[1] == Options.SourceType.WN]
        for url in self.wallpaper_net_urls:
            if url in self.wn_downloaders_cache:
                self.downloaders.append(self.wn_downloaders_cache[url])
            else:
                try:
                    dlr = WallpapersNetDownloader(self, url)
                    self.wn_downloaders_cache[url] = dlr
                    self.downloaders.append(dlr)
                except Exception:
                    logger.exception("Could not create WallpapersNetDownloader for " + url)

        self.flickr_searches = [s[2] for s in self.options.sources if s[0] and s[1] == Options.SourceType.FLICKR]
        for search in self.flickr_searches:
            if search in self.flickr_downloaders_cache:
                self.downloaders.append(self.flickr_downloaders_cache[search])
            else:
                try:
                    dlr = FlickrDownloader(self, search, lambda w, h: self.size_ok(w, h, 0))
                    self.flickr_downloaders_cache[search] = dlr
                    self.downloaders.append(dlr)
                except Exception:
                    logger.exception("Could not create FlickrDownloader for " + search)

        for downloader in self.downloaders:
            downloader.update_download_folder()
            try:
                os.makedirs(downloader.target_folder)
            except Exception:
                pass
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

        if self.events:
            for e in self.events:
                e.set()

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

        self.events = [self.change_event, self.prepare_event, self.dl_event]

    def update_indicator(self, file, is_gtk_thread):
        logger.info("Setting file info to: " + file)
        try:
            self.url = None
            label = os.path.dirname(file)
            if os.path.exists(file + ".txt"):
                with open(file + ".txt") as f:
                    lines = list(f)
                    if lines[0].strip() == "INFO:" and len(lines) == 3:
                        label = "View at " + lines[1].strip().replace("Downloaded from ", "") # TODO remove later on
                        self.url = lines[2].strip()
            if len(label) > 50:
                label = label[:50] + "..."

            trash_enabled = os.access(file, os.W_OK)
            favorites_enabled = os.access(file, os.W_OK)
            in_favs = os.path.normpath(file).startswith(os.path.normpath(self.options.favorites_folder))

            if not is_gtk_thread:
                Gdk.threads_enter()

            for i in range(10):
                self.ind.prev.set_sensitive(self.position < len(self.used) - 1)
                self.ind.file_label.set_label(os.path.basename(file))

                self.ind.trash.set_sensitive(trash_enabled)

                self.ind.favorite.set_sensitive(not in_favs)
                self.ind.favorite.set_label("Already in Favorites" if in_favs else (
                    "Move to _Favorites" if favorites_enabled else "Copy to _Favorites"))

                self.ind.show_origin.set_label(label)
                self.ind.show_origin.set_sensitive(True)

                self.update_pause_resume()

            if not is_gtk_thread:
                Gdk.threads_leave()
        except Exception:
            logger.exception("Error updating file info")

    def update_pause_resume(self):
        self.ind.pause_resume.set_label("Pause" if self.options.change_enabled else "Resume")

    def regular_change_thread(self):
        logger.info("regular_change thread running")

        if self.options.change_on_start:
            self.change_event.wait(5) # wait for prepare thread to prepare some images first
            self.change_wallpaper()

        while self.running:
            try:
                self.change_event.wait(self.options.change_interval)
                self.change_event.clear()
                if not self.running:
                    return
                if not self.options.change_enabled:
                    continue
                while (time.time() - self.last_change_time) < self.options.change_interval:
                    now = time.time()
                    wait_more = self.options.change_interval - (now - self.last_change_time)
                    self.change_event.wait(max(0, wait_more))
                if not self.options.change_enabled:
                    continue
                logger.info("regular_change changes wallpaper")
                self.change_wallpaper()
            except Exception:
                logger.exception("Exception in regular_change_thread")

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
                                        if self.options.desired_color_enabled or self.options.use_landscape_enabled or \
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
                            with self.prepared_lock:
                                self.prepared.insert(random.randint(0, 1), file) # give priority to newly-downloaded images
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
                    if self.is_image(f):
                        fp = os.path.join(dirpath, f)
                        files.append((fp, os.path.getsize(fp), os.path.getctime(fp)))
            files = sorted(files, key = lambda x: x[2])
            i = 0
            while i < len(files) and self.download_folder_size > 0.80 * mb_quota:
                file = files[i][0]
                if file != self.current:
                    try:
                        logger.debug("Deleting old file in downloaded: " + file)
                        self.remove_from_queues(file)
                        os.unlink(file)
                        self.download_folder_size -= files[i][1]
                        os.unlink(file + ".txt")
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

    def set_wp(self, filename):
        if self.set_wp_timer:
            self.set_wp_timer.cancel()
        self.set_wp_filename = filename
        self.set_wp_timer = threading.Timer(0.2, self.do_set_wp)
        self.set_wp_timer.start()

    def do_set_wp(self):
        self.set_wp_timer = None
        filename = self.set_wp_filename
        try:
            if not os.access(filename, os.R_OK):
                logger.info("Missing file or bad permissions, will not use it: " + filename)
                return

            self.update_indicator(filename, False)
            to_set = filename
            if self.filters:
                filter = self.filters[random.randint(0, len(self.filters) - 1)]
                os.system(
                    "convert \"" + filename + "\" " + filter + " " + os.path.join(self.config_folder, "wallpaper.jpg"))
                to_set = os.path.join(self.config_folder, "wallpaper.jpg")
                try:
                    with open(os.path.join(self.config_folder, "wallpaper.jpg.txt"), "w") as f:
                        f.write(filename)
                except Exception:
                    pass
            self.gsettings.set_string(self.KEY, "file://" + to_set)
            self.gsettings.apply()
            self.current = filename
            self.last_change_time = time.time()
        except Exception:
            logger.exception("Error while setting wallpaper")

    def list_images(self):
        count = 0
        for filepath in self.individual_images:
            if self.is_image(filepath) and os.access(filepath, os.R_OK):
                count += 1
                yield filepath
        folders = list(self.folders)
        random.shuffle(folders)
        for folder in folders:
            if os.path.isdir(folder):
                try:
                    for root, subFolders, files in os.walk(folder):
                        for filename in files:
                            if self.is_image(filename):
                                count += 1
                                if count > MAX_FILES:
                                    logger.info("More than %d files in the folders, stop listing" % MAX_FILES)
                                    return
                                yield os.path.join(root, filename)
                except Exception:
                    logger.exception("Cold not walk folder " + folder)

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
        self.wheel_timer = threading.Timer(0.1, self.handle_scroll)
        self.wheel_timer.start()

    def handle_scroll(self):
        if self.wheel_direction:
            self.next_wallpaper()
        else:
            self.prev_wallpaper()
        self.timer = None

    def prev_wallpaper(self, widget=None):
        if self.position >= len(self.used) - 1:
            return
        else:
            self.position += 1
            self.set_wp(self.used[self.position])

    def next_wallpaper(self, widget=None):
        if self.position > 0:
            self.position -= 1
            self.set_wp(self.used[self.position])
        else:
            self.change_wallpaper()

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
                return

            self.used = self.used[self.position:]
            self.used.insert(0, img)
            self.position = 0
            if len(self.used) > 1000:
                self.used = self.used[:1000]
            self.set_wp(img)
        except Exception:
            logger.exception("Could not change wallpaper")

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

    def size_ok(self, width, height, fuzziness):
        ok = True

        if self.options.min_size_enabled:
            ok = ok and width >= self.min_width - fuzziness * 100
            ok = ok and height >= self.min_height - fuzziness * 70

        if self.options.use_landscape_enabled:
            ok = ok and width > height

        return ok

    def open_folder(self, widget=None):
        os.system("xdg-open \"" + os.path.dirname(self.current) + "\"")

    def open_file(self, widget=None):
        os.system("xdg-open \"" + os.path.realpath(self.current) + "\"")

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

    def move_or_copy_file(self, file, to, operation):
        try:
            operation(file, to)
            try:
                operation(file + ".txt", to)
            except Exception:
                pass
            logger.info(("Moved " if operation == shutil.move else "Copied ") + file + " to " + to)
            return True
        except Exception as err:
            success = False

            if str(err).find("already exists") > 0:
                if operation == shutil.move:
                    try:
                        os.unlink(file)
                        success = True
                    except Exception:
                        pass
                else:
                    success = True

            if not success:
                logger.exception("Could not move/copy to " + to)
                op = ("Move" if operation == shutil.move else "Copy")
                dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
                    Gtk.MessageType.WARNING, Gtk.ButtonsType.OK,
                    "Could not " + op.lower() +" to " + to + ". You probably don't have permissions to " + op.lower() + " this file.")
                self.dialogs.append(dialog)
                dialog.set_title(op + " failed")
                dialog.run()
                dialog.destroy()
                self.dialogs.remove(dialog)
                return False

    def move_to_trash(self, widget=None):
        try:
            file = self.current
            url = self.url
            if not os.access(file, os.W_OK):
                dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
                    Gtk.MessageType.WARNING, Gtk.ButtonsType.OK,
                    "You don't have permissions to move %s to Trash." % file)
                self.dialogs.append(dialog)
                dialog.set_title("Cannot move")
                dialog.run()
                dialog.destroy()
                self.dialogs.remove(dialog)
            elif self.confirm_move("Move", file, "Trash"):
                trash = os.path.expanduser("~/.local/share/Trash/")
                self.move_or_copy_file(file, trash, shutil.move)
                if self.used[self.position] == file:
                    self.next_wallpaper()

                self.remove_from_queues(file)
                if url:
                    self.ban_url(url)

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

    def move_to_favorites(self, widget=None):
        try:
            file = self.current
            operation = None

            if not os.access(file, os.W_OK):
                if self.confirm_move("Copy", file, "Favorites"):
                    operation = shutil.copy
            else:
                if self.confirm_move("Move", file, "Favorites"):
                    operation = shutil.move

            if operation:
                self.move_or_copy_file(file, self.options.favorites_folder, operation)
                new_file = os.path.join(self.options.favorites_folder, os.path.basename(file))
                self.used = [(new_file if f == file else f) for f in self.used]
                if self.current == file:
                    self.current = new_file
                    self.set_wp(new_file)
                self.update_indicator(self.current, True)
        except Exception:
            logger.exception("Exception in move_to_favorites")

    def on_quit(self, widget=None):
        logger.info("Quitting")
        if self.running:
            for d in self.dialogs:
                try:
                    d.destroy()
                except Exception:
                    logger.exception("Could not destroy dialog")
                    pass
            if self.preferences_dialog:
                self.preferences_dialog.destroy()
            if self.about:
                self.about.destroy()

            self.running = False
            for e in self.events:
                e.set()

            Gtk.main_quit()

            os.unlink(os.path.expanduser("~/.config/variety/.lock"))

    def is_image(self, filename):
        return filename.lower().endswith(('.jpg', '.jpeg', '.gif', '.png', '.tiff'))

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
        self.update_indicator(self.current, True)
