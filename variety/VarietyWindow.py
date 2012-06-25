# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

import gettext
from gettext import gettext as _

gettext.textdomain('variety')

from gi.repository import Gtk # pylint: disable=E0611
import logging

logger = logging.getLogger('variety')

from variety_lib import Window
from variety.AboutVarietyDialog import AboutVarietyDialog
from variety.PreferencesVarietyDialog import PreferencesVarietyDialog

from gi.repository import Gio

import os
import shutil
import random

from AvgColor import AvgColor
from WallpapersNetScraper import WallpapersNetScraper

import threading
import time

# See variety_lib.Window.py for more details about how this class works
class VarietyWindow(Window) :
    __gtype_name__ = "VarietyWindow"

    SCHEMA = 'org.gnome.desktop.background'
    KEY = 'picture-uri'

    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the main window"""
        super(VarietyWindow, self).finish_initializing(builder)

        self.gsettings = Gio.Settings.new(self.SCHEMA)

        self.AboutDialog = AboutVarietyDialog
        self.PreferencesDialog = PreferencesVarietyDialog

        #self.folder = "/d/Pics/Wallpapers/"
        #self.folder = "/usr/share/backgrounds/"
        self.folder = "/d/_linux/"
        self.change_interval = 30
        self.dl_interval = 20
        self.avg_color = None

        self.config_dir = os.path.join(os.getenv("HOME"), ".variety")
        self.dl_dir = os.path.join(self.config_dir, "downloaded")
        try:
            os.makedirs(self.dl_dir)
        except OSError:
            pass

        #self.wn_url = "http://wallpapers.net/nature-desktop-wallpapers.html"
        self.wn_url = "http://wallpapers.net/top_wallpapers/"

        self.used = []
        self.used.append(self.gsettings.get_string(self.KEY).replace("file://", ""))
        self.position = 0

        self.image_count = 0

        random.seed()

        self.image_cache = {}

        self.prepared = []
        self.change_event = threading.Event()

        self.change_thread = threading.Thread(target=self.regular_change)
        self.change_thread.daemon = True
        self.change_thread.start()

        self.prepare_thread = threading.Thread(target=self.prepare)
        self.prepare_thread.daemon = True
        self.prepare_thread.start()

        self.dl_thread = threading.Thread(target=self.download)
        self.dl_thread.daemon = True
        self.dl_thread.start()

        self.update_current_file_info()

    def update_current_file_info(self):
        file = self.used[self.position]
        logger.info("Setting file info to: " + file)

        try:
            self.file_label.set_label(os.path.basename(file))

            if os.path.exists(file + ".txt"):
                with open(file + ".txt") as f:
                    lines = list(f)
                    if lines[0].strip() == "INFO:":
                        self.show_origin.set_label(lines[1].strip())
                        self.show_origin.set_sensitive(True)
                        self.url = lines[2].strip()
                        return
            self.show_origin.set_label("Unknown origin")
            self.show_origin.set_sensitive(False)
            self.url = None
        except Exception:
            logger.exception("Error updating file info")

    def regular_change(self):
        logger.info("regular_change thread running")
        while True:
            time.sleep(self.change_interval)
            logger.info("regular_change changes wallpaper")
            self.change_wallpaper()

    def prepare(self):
        logger.info("prepare thread running")
        while True:
            logger.info("preparing some images")
            cnt = 0
            while len(self.prepared) < 10:
                img = self.prepare_image()
                if img:
                    self.prepared.append(img)
                cnt += 1
                if cnt >= self.image_count // 10:
                    logger.info("could not prepare 10 images")
                    break

            self.change_event.clear()
            self.change_event.wait(5)

    def download(self):
        while True:
            try:
                wns = WallpapersNetScraper(self.wn_url, self.dl_dir)
                time.sleep(self.dl_interval)
                wns.download_one()
            except Exception, err:
                logger.exception("Could not download wallpaper:")

    def set_wp(self, filename):
        try:
            self.update_current_file_info()
            self.gsettings.set_string(self.KEY, "file://" + filename)
            self.gsettings.apply()
        except Exception:
            logger.exception("Error while setting wallpaper")

    def select_random_image(self, dirs):
        cnt = 0
        if self.image_count < 20 or random.randint(0, 20) == 0:
            for dir in dirs:
                for root, subFolders, files in os.walk(dir):
                    for filename in files:
                        if filename.lower().endswith(('.jpg', '.jpeg', '.gif', '.png')):
                            cnt += 1
            if not cnt:
                return None

            self.image_count = cnt
        else:
            cnt = self.image_count

        r = random.randint(0, cnt - 1)

        for dir in dirs:
            for root, subFolders, files in os.walk(dir):
                for filename in files:
                    if filename.lower().endswith(('.jpg', '.jpeg', '.gif', '.png')):
                        if r == 0:
                            return os.path.join(root, filename)
                        r -= 1
            # fallback - select some image if r never reaches 0 (can happen due to intermediate deletions)
        for dir in dirs:
            for root, subFolders, files in os.walk(dir):
                for filename in files:
                    if filename.lower().endswith(('.jpg', '.jpeg', '.gif', '.png')):
                        return os.path.join(root, filename)

        return None

    def on_indicator_scroll(self, indicator, steps, direction, data=None):
        # direction is 0 or 1
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

    def prepare_image(self):
        img = self.select_random_image([self.folder, self.dl_dir])
        if not img:
            return

        #print("testing " + img)
        if self.image_ok(img):
            #print("ok")
            return img

    def change_wallpaper(self, widget=None, data=None):
        img = None

        if len(self.prepared):
            img = self.prepared.pop()
            self.change_event.set()
        else:
            for i in xrange(10):
                img = self.prepare_image()
                if img:
                    break

        if not img:
            img = self.select_random_image([self.folder, self.dl_dir])
        if not img:
            return

        self.used = self.used[self.position:]
        self.used.insert(0, img)
        self.position = 0
        if len(self.used) > 1000:
            self.used = self.used[:1000]
        self.set_wp(img)

    def image_ok(self, img):
        return img != self.used[self.position] and self.color_ok(img)

    def color_ok(self, img):
        if not self.avg_color:
            return True
        try:
            if not img in self.image_cache:
                avg = AvgColor(img)
                self.image_cache[img] = avg.getAvg()
            avg = self.image_cache[img]
            r, g, b = avg
            #print(avg)
            tr, tg, tb = self.avg_color
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

    def move_to_trash(self, widget=None, data=None):
        file = self.used[self.position]

        dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
            Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO,
            "You are going to move the file " + file + " to Trash. Are you sure?")
        dialog.set_title("Confirm Move to Trash")

        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            print "deleting"
            try:
                self.next_wallpaper()
                self.used.remove(file)
                trash = os.path.join(os.getenv("HOME"), ".local/share/Trash/")
                shutil.move(file, trash)
                shutil.move(file + ".txt", trash)
            except Exception:
                logger.exception("Could not move to Trash")


