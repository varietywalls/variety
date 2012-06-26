# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

import gettext
from gettext import gettext as _

gettext.textdomain('variety')

from gi.repository import Gtk, Gio # pylint: disable=E0611

from variety_lib import Window
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

from AvgColor import AvgColor
from WallpapersNetScraper import WallpapersNetScraper
from Options import Options

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

        self.config_folder = os.path.expanduser("~/.variety")
        self.download_folder = os.path.join(self.config_folder, "Downloaded")
        self.favorites_folder = os.path.join(self.config_folder, "Favorites")

        try:
            os.makedirs(self.download_folder)
        except OSError:
            pass

        # load config
        self.reload_config()


        self.used = []
        self.used.append(self.gsettings.get_string(self.KEY).replace("file://", ""))
        self.position = 0

        self.last_change_time = 0

        self.image_count = 0
        self.image_cache = {}
        #TODO load image cache

        self.update_current_file_info()
        self.start_threads()

    def reload_config(self):
        options = Options()
        options.read()

        self.change_on_start = options.change_on_start
        self.change_interval = options.change_interval
        self.download_interval = options.change_interval
        self.desired_color = options.desired_color

        self.favorites_folder = options.favorites_folder
        try:
            os.makedirs(self.favorites_folder)
        except OSError:
            pass

        self.individual_images = [s[2] for s in options.sources if s[0] and s[1] == Options.SourceType.IMAGE]
        self.folders = [s[2] for s in options.sources if s[0] and s[1] == Options.SourceType.FOLDER]
        if not self.favorites_folder in self.folders:
            self.folders.append(self.favorites_folder)
        self.wallpaper_net_urls = [s[2] for s in options.sources if s[0] and s[1] == Options.SourceType.WN]

        if self.wallpaper_net_urls:
            self.folders.append(self.download_folder)
        self.wn_downloaders = [WallpapersNetScraper(url, self.download_folder) for url in self.wallpaper_net_urls]

        self.filters = [f[2] for f in options.filters if f[0]]

        logger.info("Loaded options:")
        logger.info("Folders: " + str(self.folders))
        logger.info("WN URLs: " + str(self.wallpaper_net_urls))
        logger.info("Filters: " + str(self.filters))

    def start_threads(self):
        self.running = True
        self.quit_event = threading.Event()

        self.prepared = []
        self.change_event = threading.Event()

        self.change_thread = threading.Thread(target=self.regular_change_thread)
        self.change_thread.daemon = True
        self.change_thread.start()

        self.prepare_thread = threading.Thread(target=self.prepare_thread)
        self.prepare_thread.daemon = True
        self.prepare_thread.start()

        self.dl_thread = threading.Thread(target=self.download_thread)
        self.dl_thread.daemon = True
        self.dl_thread.start()

    def update_current_file_info(self):
        file = self.used[self.position]
        logger.info("Setting file info to: " + file)

        try:
            self.ind.file_label.set_label(os.path.basename(file))

            self.ind.favorite.set_sensitive(
                not os.path.normpath(file).startswith(os.path.normpath(self.favorites_folder)))

            if os.path.exists(file + ".txt"):
                with open(file + ".txt") as f:
                    lines = list(f)
                    if lines[0].strip() == "INFO:":
                        self.ind.show_origin.set_label(lines[1].strip())
                        self.ind.show_origin.set_sensitive(True)
                        self.url = lines[2].strip()
                        return
            self.ind.show_origin.set_label("Unknown origin")
            self.ind.show_origin.set_sensitive(False)
            self.url = None
        except Exception:
            logger.exception("Error updating file info")

    def regular_change_thread(self):
        logger.info("regular_change thread running")

        if self.change_on_start:
            self.change_wallpaper()

        while self.running:
            self.quit_event.wait(self.change_interval)
            if not self.running:
                return
            while (time.time() - self.last_change_time) < self.change_interval:
                now = time.time()
                wait_more = self.change_interval - (now - self.last_change_time)
                time.sleep(max(0, wait_more))
            logger.info("regular_change changes wallpaper")
            self.change_wallpaper()

    def prepare_thread(self):
        logger.info("prepare thread running")
        while self.running:
            if not self.prepared or (len(self.prepared) < min(10, self.image_count // 20)):
                logger.info("preparing some images")
                images = self.select_random_images(100)
                for img in images:
                    if self.image_ok(img):
                        self.prepared.append(img)
                if not self.prepared:
                    self.prepared.extend(list(images[:5]))
                logger.info("prepared buffer contains %s images" % len(self.prepared))

            self.change_event.clear()
            self.change_event.wait(30)

    def download_thread(self):
        while self.running:
            try:
                self.quit_event.wait(self.download_interval)
                if not self.running:
                    return
                if self.wn_downloaders:
                    downloader = self.wn_downloaders[random.randint(0, len(self.wn_downloaders) - 1)]
                    downloader.download_one()
            except Exception:
                logger.exception("Could not download wallpaper:")

    def set_wp(self, filename):
        try:
            self.update_current_file_info()
            if self.filters:
                filter = self.filters[random.randint(0, len(self.filters) - 1)]
                os.system("convert " + filename + " " + filter + " " + os.path.join(self.config_folder, "wallpaper.jpg"))
                filename = os.path.join(self.config_folder, "wallpaper.jpg")
            self.gsettings.set_string(self.KEY, "file://" + filename)
            self.gsettings.apply()
            self.last_change_time = time.time()
        except Exception:
            logger.exception("Error while setting wallpaper")

    def list_images(self):
        for filepath in self.individual_images:
            if self.is_image(filepath) and os.access(filepath, os.F_OK):
                yield filepath
        for folder in self.folders:
            if os.path.isdir(folder):
                try:
                    for root, subFolders, files in os.walk(folder):
                        for filename in files:
                            if self.is_image(filename):
                                yield os.path.join(root, filename)
                except Exception:
                    logger.exception("Cold not walk folder " + folder)

    def select_random_images(self, count):
        if self.image_count < 20 or random.randint(0, 20) == 0:
            cnt = sum(1 for f in self.list_images())
            if not cnt:
                return []

            self.image_count = cnt
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
                    return result

        return result

    def on_indicator_scroll(self, indicator, steps, direction, data=None):
        if direction == 0:
            self.prev_wallpaper()
        else:
            self.next_wallpaper()

    def prev_wallpaper(self):
        if self.position >= len(self.used) - 1:
            return
        else:
            self.position += 1
            self.set_wp(self.used[self.position])

    def next_wallpaper(self):
        if self.position > 0:
            self.position -= 1
            self.set_wp(self.used[self.position])
        else:
            self.change_wallpaper()

    def change_wallpaper(self, widget=None, data=None):
        try:
            if len(self.prepared):
                img = self.prepared.pop()
                self.change_event.set()
            else:
                rnd_images = self.select_random_images(1)
                img = rnd_images[0] if rnd_images else None

            if not img:
                return

            self.used = self.used[self.position:]
            self.used.insert(0, img)
            self.position = 0
            if len(self.used) > 1000:
                self.used = self.used[:1000]
            self.set_wp(img)
        except Exception:
            logger.exception("Could not change wallpaper")

    def image_ok(self, img):
        return img != self.used[self.position] and self.color_ok(img)

    def color_ok(self, img):
        if not self.desired_color:
            return True
        try:
            if not img in self.image_cache:
                avg = AvgColor(img)
                self.image_cache[img] = avg.getAvg()
            avg = self.image_cache[img]
            r, g, b = avg
            tr, tg, tb = self.desired_color
            return abs(r - tr) < 40 and abs(g - tg) < 40 and abs(b - tb) < 40
        except Exception, err:
            logger.exception("Error with AvgColor:")
            return False

    def open_folder(self, widget=None, data=None):
        os.system("xdg-open " + os.path.dirname(self.used[self.position]))

    def open_file(self, widget=None, data=None):
        os.system("xdg-open " + self.used[self.position])

    def on_show_origin(self, widget=None, data=None):
        if self.url:
            os.system("xdg-open " + self.url)

    def confirm_move(self, file, to):
        dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
            Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO,
            "Move " + os.path.basename(file) + " to " + to + ". Are you sure?")
        dialog.set_title("Confirm Move to " + to)
        response = dialog.run()
        dialog.destroy()
        return response

    def move_file(self, file, to):
        try:
            shutil.move(file, to)
            shutil.move(file + ".txt", to)
            logger.info("Moved " + file + " to " + to)
        except Exception:
            logger.exception("Could not move to " + to)

    def move_to_trash(self, widget=None, data=None):
        file = self.used[self.position]
        if self.confirm_move(file, "Trash") == Gtk.ResponseType.YES:
            while self.used[self.position] == file:
                self.next_wallpaper()
            self.used = [f for f in self.used if f != file]
            trash = os.path.expanduser("~/.local/share/Trash/")
            self.move_file(file, trash)

    def move_to_favorites(self, widget=None, data=None):
        file = self.used[self.position]
        if self.confirm_move(file, "Favorites") == Gtk.ResponseType.YES:
            new_file = os.path.join(self.favorites_folder, os.path.basename(file))
            self.used = [(new_file if f == file else f) for f in self.used]
            self.move_file(file, self.favorites_folder)
            self.update_current_file_info()

    def on_quit(self, widget=None):
        logger.info("Quitting")
        if self.running:
            self.running = False
            self.quit_event.set()
            Gtk.main_quit()
            os.unlink(os.path.expanduser("~/.variety/.lock"))

    def is_image(self, filename):
        return filename.lower().endswith(('.jpg', '.jpeg', '.gif', '.png'))

    def first_run(self):
        fr_file = os.path.join(self.config_folder, ".firstrun")
        if not os.path.exists(fr_file):
            f = open(fr_file, "w")
            f.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            f.close()
            self.show()

    def on_continue_clicked(self, button=None):
        self.destroy()
