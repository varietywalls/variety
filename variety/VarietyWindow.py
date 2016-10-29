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
import io

import datetime

from variety import _, _u
import subprocess
import urllib
from variety.VarietyOptionParser import VarietyOptionParser
from variety.FacebookHelper import FacebookHelper
from jumble.Jumble import Jumble

from gi.repository import Gtk, Gdk, GdkPixbuf, GObject, Gio, Notify # pylint: disable=E0611

Notify.init("Variety")

from variety_lib import varietyconfig

import os
import stat
import shutil
import threading
import time
import logging
import random
import re
import urlparse
import webbrowser
from PIL import Image as PILImage

random.seed()
logger = logging.getLogger('variety')

from variety.AboutVarietyDialog import AboutVarietyDialog
from variety.WelcomeDialog import WelcomeDialog
from variety.PreferencesVarietyDialog import PreferencesVarietyDialog
from variety.FacebookFirstRunDialog import FacebookFirstRunDialog
from variety.FacebookPublishDialog import FacebookPublishDialog
from variety.DominantColors import DominantColors
from variety.WallhavenDownloader import WallhavenDownloader
from variety.RedditDownloader import RedditDownloader
from variety.BingDownloader import BingDownloader
from variety.UnsplashDownloader import UnsplashDownloader
from variety.PanoramioDownloader import PanoramioDownloader
from variety.DesktopprDownloader import DesktopprDownloader
from variety.APODDownloader import APODDownloader
from variety.FlickrDownloader import FlickrDownloader
from variety.MediaRssDownloader import MediaRssDownloader
from variety.EarthDownloader import EarthDownloader, EARTH_ORIGIN_URL
from variety.Options import Options
from variety.ImageFetcher import ImageFetcher
from variety.Util import Util, throttle, debounce
from variety.ThumbsManager import ThumbsManager
from variety.QuotesEngine import QuotesEngine
from variety.QuoteWriter import QuoteWriter
from variety.Smart import Smart
from variety.Stats import Stats
from variety import indicator


DL_FOLDER_FILE = ".variety_download_folder"

DONATE_URL = 'https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=DHQUELMQRQW46&lc=BG&item_name=' \
             'Variety%20Wallpaper%20Changer&currency_code=EUR&bn=PP%2dDonationsBF%3abtn_donate_SM%2egif%3aNonHosted'

OUTDATED_MSG = 'This version of Variety is outdated and unsupported. Please upgrade. Quitting.'


class VarietyWindow(Gtk.Window):
    __gtype_name__ = "VarietyWindow"

    #SERVERSIDE_OPTIONS_URL = "http://tiny.cc/variety-options-051"
    SERVERSIDE_OPTIONS_URL = "http://localhost:8000/options"

    OUTDATED_SET_WP_SCRIPTS = {
        "b8ff9cb65e3bb7375c4e2a6e9611c7f8",
        "3729d3e1f57aa1159988ba2c8f929389",
        "feafa658d9686ecfabdbcf236c32fd0f",
        "83d8ebeec3676474bdd90c55417e8640",
        "1562cb289319aa39ac1b37a8ee4c0103",
        "6c54123e87e98b15d87f0341d3e36fc5",
        "3f9fcc524bfee8fb146d1901613d3181",
        "40db8163e22fbe8a505bfd1280190f0d",  # 0.4.14, 0.4.15
        "59a037428784caeb0834a8dd7897a88b",  # 0.4.16, 0.4.17
        "e4510e39fd6829ef550e128a1a4a036b",  # 0.4.18
        "d8d6a6c407a3d02ee242e9ce9ceaf293",  # 0.4.19
        "fdb69a2b16c62594c0fc12318ec58023",  # 0.4.20
        "236fa00c42af82904eaaecf2d460d21f",  # 0.5.5
    }

    OUTDATED_GET_WP_SCRIPTS = {
        "d8df22bf24baa87d5231e31027e79ee5",
        "822aee143c6b3f1166e5d0a9c637dd16",  # 0.4.16, 0.4.17
        "367f629e2f24ad8040e46226b18fdc81",  # 0.4.18, 0.4.19
    }

    @classmethod
    def get_instance(cls):
        return VarietyWindow.instance

    def __init__(self):
        VarietyWindow.instance = self

    def start(self, cmdoptions):
        self.running = True

        self.about = None
        self.preferences_dialog = None
        self.ind = None

        try:
            if Gio.SettingsSchemaSource.get_default().lookup("org.gnome.desktop.background", True):
                self.gsettings = Gio.Settings.new('org.gnome.desktop.background')
            else:
                self.gsettings = None
        except Exception:
            self.gsettings = None

        self.thumbs_manager = ThumbsManager(self)

        self.quotes_engine = None
        self.quote = None
        self.quote_favorites_contents = ''
        self.clock_thread = None
        self.reporting_thread = None

        self.prepare_config_folder()
        self.perform_upgrade()

        self.events = []

        self.create_downloaders_cache()

        self.prepared = []
        self.prepared_cleared = False
        self.prepared_lock = threading.Lock()
        self.prepared_from_downloads = []

        self.downloaded = []

        self.register_clipboard()

        self.do_set_wp_lock = threading.Lock()
        self.auto_changed = True

        self.process_command(cmdoptions, initial_run=True)

        # load config
        self.options = None
        self.server_options = {}
        self.load_banned()
        self.load_history()
        self.post_filter_filename = None

        if self.position < len(self.used):
            self.thumbs_manager.mark_active(file=self.used[self.position], position=self.position)

        self.jumble = Jumble([os.path.join(varietyconfig.get_data_path(), "plugins"), self.plugins_folder])

        setattr(self.jumble, "parent", self)
        self.jumble.load()

        self.image_count = -1
        self.image_colors_cache = {}

        self.smart = Smart(self)

        self.reload_config()
        self.load_last_change_time()

        self.update_indicator(auto_changed=False)

        self.start_threads()

        prepare_earth_timer = threading.Timer(0, self.prepare_earth_downloader)
        prepare_earth_timer.start()

        self.dialogs = []

        self.first_run()

        def _delayed():
            self.create_preferences_dialog()
            self.smart.reload()
        GObject.timeout_add(1000, _delayed)

    def on_mnu_about_activate(self, widget, data=None):
        """Display the about box for variety."""
        if self.about is not None:
            logger.debug(lambda: 'show existing about_dialog')
            self.about.set_keep_above(True)
            self.about.present()
            self.about.set_keep_above(False)
            self.about.present()
        else:
            logger.debug(lambda: 'create new about dialog')
            self.about = AboutVarietyDialog() # pylint: disable=E1102
            self.about.run()
            self.about.destroy()
            self.about = None

    def on_mnu_donate_activate(self, widget, data=None):
        self.preferences_dialog.ui.notebook.set_current_page(8)
        self.on_mnu_preferences_activate()
        webbrowser.open_new_tab(DONATE_URL)

    def get_preferences_dialog(self):
        if not self.preferences_dialog:
            self.create_preferences_dialog()
        return self.preferences_dialog

    def create_preferences_dialog(self):
        if not self.preferences_dialog:
            logger.debug(lambda: 'create new preferences_dialog')
            self.preferences_dialog = PreferencesVarietyDialog(parent=self) # pylint: disable=E1102

            def _on_preferences_dialog_destroyed(widget, data=None):
                logger.debug(lambda: 'on_preferences_dialog_destroyed')
                self.preferences_dialog = None
            self.preferences_dialog.connect('destroy', _on_preferences_dialog_destroyed)

            def _on_preferences_close_button(arg1, arg2):
                self.preferences_dialog.close()
                return True
            self.preferences_dialog.connect('delete_event', _on_preferences_close_button)

    def on_mnu_preferences_activate(self, widget=None, data=None):
        """Display the preferences window for variety."""
        if self.preferences_dialog is not None:
            if self.preferences_dialog.get_visible():
                logger.debug(lambda: 'bring to front existing and visible preferences_dialog')
                self.preferences_dialog.set_keep_above(True)
                self.preferences_dialog.present()
                self.preferences_dialog.set_keep_above(False)
                self.preferences_dialog.present()
            else:
                logger.debug(lambda: 'reload and show existing but non-visible preferences_dialog')
                self.preferences_dialog.reload()
                self.preferences_dialog.show()
        else:
            self.create_preferences_dialog()
            self.preferences_dialog.show()
            # destroy command moved into dialog to allow for a help button

    def prepare_config_folder(self):
        self.config_folder = os.path.expanduser(u"~/.config/variety")
        Util.makedirs(self.config_folder)

        shutil.copy(varietyconfig.get_data_file("config", "variety.conf"),
                    os.path.join(self.config_folder, "variety_latest_default.conf"))

        if not os.path.exists(os.path.join(self.config_folder, "variety.conf")):
            logger.info(lambda: "Missing config file, copying it from " +
                        varietyconfig.get_data_file("config", "variety.conf"))
            shutil.copy(varietyconfig.get_data_file("config", "variety.conf"), self.config_folder)

        if not os.path.exists(os.path.join(self.config_folder, "ui.conf")):
            logger.info(lambda: "Missing ui.conf file, copying it from " +
                        varietyconfig.get_data_file("config", "ui.conf"))
            shutil.copy(varietyconfig.get_data_file("config", "ui.conf"), self.config_folder)

        self.plugins_folder = os.path.join(self.config_folder, "plugins")
        Util.makedirs(self.plugins_folder)

        self.scripts_folder = os.path.join(self.config_folder, "scripts")
        Util.makedirs(self.scripts_folder)

        if not os.path.exists(os.path.join(self.scripts_folder, "set_wallpaper")):
            logger.info(lambda: "Missing set_wallpaper file, copying it from " +
                        varietyconfig.get_data_file("scripts", "set_wallpaper"))
            shutil.copy(varietyconfig.get_data_file("scripts", "set_wallpaper"), self.scripts_folder)

        if not os.path.exists(os.path.join(self.scripts_folder, "get_wallpaper")):
            logger.info(lambda: "Missing get_wallpaper file, copying it from " +
                        varietyconfig.get_data_file("scripts", "get_wallpaper"))
            shutil.copy(varietyconfig.get_data_file("scripts", "get_wallpaper"), self.scripts_folder)

        # make all scripts executable:
        for f in os.listdir(self.scripts_folder):
            path = os.path.join(self.scripts_folder, f)
            os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

        self.wallpaper_folder = os.path.join(self.config_folder, "wallpaper")
        Util.makedirs(self.wallpaper_folder)

        # TODO: Sort of hacky to have filter-related code here, they should be more isolated
        pencil_tile_filename = os.path.join(self.config_folder, "pencil_tile.png")
        if not os.path.exists(pencil_tile_filename):
            def _generate_pencil_tile():
                logger.info(lambda: "Missing pencil_tile.png file, generating it " +
                            varietyconfig.get_data_file("media", "pencil_tile.png"))
                try:
                    os.system(
                        "convert -size 1000x1000 xc: +noise Random -virtual-pixel tile "
                        "-motion-blur 0x20+135 -charcoal 2 -resize 50%% \"%s\"" % pencil_tile_filename.encode('utf8'))
                except Exception:
                    logger.exception(lambda: "Could not generate pencil_tile.png")
            threading.Timer(0, _generate_pencil_tile).start()

    def register_clipboard(self):
        def clipboard_changed(clipboard, event):
            try:
                if not self.options.clipboard_enabled:
                    return

                text = clipboard.wait_for_text()
                logger.debug(lambda: "Clipboard: %s" % text)
                if not text:
                    return

                valid = [url for url in text.split('\n') if
                         ImageFetcher.url_ok(url, self.options.clipboard_use_whitelist, self.options.clipboard_hosts)]

                if valid:
                    logger.info(lambda: "Received clipboard URLs: " + str(valid))
                    self.process_urls(valid, verbose=False)
            except Exception:
                logger.exception(lambda: "Exception when processing clipboard:")

        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.clipboard.connect("owner-change", clipboard_changed)

    def log_options(self):
        logger.info(lambda: "Loaded options:")
        for k, v in sorted(self.options.__dict__.items()):
            logger.info(lambda: "%s = %s" % (k, v))
#        pprint(self.options.__dict__, indent=0)

    def get_real_download_folder(self):
        subfolder = "Downloaded by Variety"
        dl = self.options.download_folder

        # If chosen folder is within Variety's config folder, or folder's name is "Downloaded by Variety",
        # or folder is missing or it is empty or it has already been used as a download folder, then use it:
        if Util.file_in(dl, self.config_folder) or \
                dl.endswith("/%s" % subfolder) or dl.endswith("/%s/" % subfolder) or \
                not os.path.exists(dl) or not os.listdir(dl) or \
                os.path.exists(os.path.join(dl, DL_FOLDER_FILE)):
            return dl
        else:
            # In all other cases (i.e. it is an existing user folder with files in it), use a subfolder inside it
            return os.path.join(dl, subfolder)

    def prepare_download_folder(self):
        self.real_download_folder = self.get_real_download_folder()
        if self.preferences_dialog:
            GObject.idle_add(self.preferences_dialog.update_real_download_folder)

        Util.makedirs(self.real_download_folder)
        dl_folder_file = os.path.join(self.real_download_folder, DL_FOLDER_FILE)
        if not os.path.exists(dl_folder_file):
            with open(dl_folder_file, "w") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

    def reload_config(self):
        self.previous_options = self.options

        self.options = Options()
        self.options.read()

        GObject.idle_add(self.update_indicator_icon)

        self.prepare_download_folder()

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
            logger.info(lambda: "Size/landscape settings changed - purging downloaders cache")
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
                    logger.info(lambda: "Creating new downloader for type %d, location %s" % (type, location))
                    dlr = self.create_downloader(type, location)
                    self.downloaders_cache[type][location] = dlr
                    self.downloaders.append(dlr)
                except Exception:
                    logger.exception(lambda: "Could not create Downloader for type %d, location %s" % (type, location))

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
        if self.should_clear_prepared():
            self.clear_prepared_queue()
        else:
            logger.info(lambda: "No need to clear prepared queue")

        self.start_clock_thread()
        self.start_reporting_thread()

        if self.options.quotes_enabled:
            if not self.quotes_engine:
                self.quotes_engine = QuotesEngine(self)
            self.quotes_engine.start()
        else:
            if self.quotes_engine:
                self.quotes_engine.stop()

        if self.quotes_engine:
            self.reload_quote_favorites_contents()
            clear_prepared = self.previous_options is None or \
                self.options.quotes_disabled_sources != self.previous_options.quotes_disabled_sources or \
                self.options.quotes_tags != self.previous_options.quotes_tags or \
                self.options.quotes_authors != self.previous_options.quotes_authors
            self.quotes_engine.on_options_updated(clear_prepared=clear_prepared)

        if self.previous_options and (
                self.options.filters != self.previous_options.filters or
                self.options.quotes_enabled != self.previous_options.quotes_enabled or
                self.options.clock_enabled != self.previous_options.clock_enabled):
            self.no_effects_on = None

        def _update_indicator():
            self.update_indicator(auto_changed=False)
        GObject.idle_add(_update_indicator)

        if self.previous_options is None or self.options.filters != self.previous_options.filters:
            threading.Timer(0.1, self.refresh_wallpaper).start()
        else:
            threading.Timer(0.1, self.refresh_texts).start()

        if self.preferences_dialog:
            self.smart.reload()

        if self.events:
            for e in self.events:
                e.set()

    def clear_prepared_queue(self):
        self.filters_warning_shown = False
        logger.info(lambda: "Clearing prepared queue")
        with self.prepared_lock:
            self.prepared_cleared = True
            self.prepared = []
            self.prepared_from_downloads = []
            self.prepare_event.set()
        self.image_count = -1

    def should_clear_prepared(self):
        return self.previous_options and (
               [s for s in self.previous_options.sources if s[0]] != [s for s in self.options.sources if s[0]] or \
               self.filtering_options_changed())

    def filtering_options_changed(self):
        if not self.previous_options:
            return False
        if self.size_options_changed():
            return True
        if self.previous_options.safe_mode != self.options.safe_mode:
            return True
        if self.previous_options.desired_color_enabled != self.options.desired_color_enabled or \
            self.previous_options.desired_color != self.options.desired_color:
            return True
        if self.previous_options.lightness_enabled != self.options.lightness_enabled or \
            self.previous_options.lightness_mode != self.options.lightness_mode:
            return True
        if self.previous_options.min_rating_enabled != self.options.min_rating_enabled or \
            self.previous_options.min_rating != self.options.min_rating:
            return True
        return False

    def size_options_changed(self):
        return self.previous_options and (
            self.previous_options.min_size_enabled != self.options.min_size_enabled or \
            self.previous_options.min_size != self.options.min_size or \
            self.previous_options.use_landscape_enabled != self.options.use_landscape_enabled)

    def create_downloaders_cache(self):
        self.downloaders_cache = {}
        for type in Options.SourceType.dl_types:
            self.downloaders_cache[type] = {}

    def create_downloader(self, type, location):
        if type == Options.SourceType.DESKTOPPR:
            return DesktopprDownloader(self)
        elif type == Options.SourceType.APOD:
            return APODDownloader(self)
        elif type == Options.SourceType.EARTH:
            return EarthDownloader(self)
        elif type == Options.SourceType.FLICKR:
            return FlickrDownloader(self, location)
        elif type == Options.SourceType.WALLHAVEN:
            return WallhavenDownloader(self, location)
        elif type == Options.SourceType.REDDIT:
            return RedditDownloader(self, location)
        elif type == Options.SourceType.BING:
            return BingDownloader(self)
        elif type == Options.SourceType.UNSPLASH:
            return UnsplashDownloader(self)
        elif type == Options.SourceType.MEDIA_RSS:
            return MediaRssDownloader(self, location)
        elif type == Options.SourceType.PANORAMIO:
            return PanoramioDownloader(self, location)
        elif type == Options.SourceType.RECOMMENDED:
            if self.smart.user:
                return MediaRssDownloader(self, '%s/user/%s/recommended/rss' % (Smart.SITE_URL, self.smart.user["id"]))
            else:
                raise Exception('No Smart user yet, not a problem')
        elif type == Options.SourceType.LATEST:
            return MediaRssDownloader(self, Smart.SITE_URL + '/rss')
        else:
            raise Exception("Unknown downloader type")

    def get_folder_of_source(self, source):
        type = source[1]
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

    def delete_files_of_source(self, source):
        folder = self.get_folder_of_source(source)
        if Util.file_in(folder, self.real_download_folder):
            self.remove_folder_from_queues(folder)
            should_repaint = \
                self.thumbs_manager.is_showing("history") or self.thumbs_manager.is_showing("downloads") or (
                self.thumbs_manager.get_folders() is not None and folder in self.thumbs_manager.get_folders())

            if should_repaint:
                self.thumbs_manager.repaint()
            try:
                logger.info(lambda: "Deleting recursively folder " + folder)
                shutil.rmtree(folder)
            except Exception:
                logger.exception(lambda: "Could not delete download folder contents " + folder)
            if self.current and Util.file_in(self.current, folder):
                change_timer = threading.Timer(0, self.next_wallpaper)
                change_timer.start()

    def load_banned(self):
        self.banned = set()
        try:
            with io.open(os.path.join(self.config_folder, "banned.txt"), encoding='utf8') as f:
                for line in f:
                    self.banned.add(line.strip())
        except Exception:
            logger.info(lambda: "Missing or invalid banned URLs list, no URLs will be banned")

    def start_clock_thread(self):
        if not self.clock_thread and self.options.clock_enabled:
            self.clock_event = threading.Event()
            self.events.append(self.clock_event)
            self.clock_thread = threading.Thread(target=self.clock_thread_method)
            self.clock_thread.daemon = True
            self.clock_thread.start()

    def start_reporting_thread(self):
        if not self.reporting_thread and self.options.stats_enabled:
            self.reporting_thread = threading.Thread(target=self.reporting_thread_method)
            self.reporting_thread.daemon = True
            self.reporting_thread.start()

    def start_threads(self):
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

        self.events.extend([self.change_event, self.prepare_event, self.dl_event])

        server_options_thread = threading.Thread(target=self.server_options_thread)
        server_options_thread.daemon = True
        server_options_thread.start()

    def is_in_favorites(self, file):
        filename = os.path.basename(file)
        return os.path.exists(os.path.join(self.options.favorites_folder, filename))

    def is_current_refreshable(self):
        #TODO this is a hacky check, but works while EarthDownloader is the only refreshing downloader
        return self.url == EARTH_ORIGIN_URL

    def update_favorites_menuitems(self, holder, auto_changed, favs_op):
        if auto_changed:
            # delay enabling Move/Copy operations in this case - see comment below
            holder.copy_to_favorites.set_sensitive(False)
            holder.move_to_favorites.set_sensitive(False)
        else:
            holder.copy_to_favorites.set_sensitive(favs_op in ("copy", "both"))
            holder.move_to_favorites.set_sensitive(favs_op in ("move", "both"))
        if favs_op is None:
            holder.copy_to_favorites.set_visible(False)
            holder.move_to_favorites.set_visible(False)
        elif favs_op is "favorite":
            holder.copy_to_favorites.set_label(_("Already in Favorites"))
            holder.copy_to_favorites.set_visible(True)
            holder.move_to_favorites.set_visible(False)
        else:
            holder.copy_to_favorites.set_label(_("Copy to _Favorites"))
            holder.move_to_favorites.set_label(_("Move to _Favorites"))
            if favs_op == "copy":
                holder.copy_to_favorites.set_visible(True)
                holder.move_to_favorites.set_visible(False)
            elif favs_op == "move":
                holder.copy_to_favorites.set_visible(False)
                holder.move_to_favorites.set_visible(True)
            else: # both
                holder.move_to_favorites.set_label(_("Move to Favorites"))
                holder.copy_to_favorites.set_visible(True)
                holder.move_to_favorites.set_visible(True)

    def update_indicator(self, file=None, is_gtk_thread=True, auto_changed=None):
        if not file:
            file = self.current
        if auto_changed is None:
            auto_changed = self.auto_changed

        logger.info(lambda: "Setting file info to: %s" % file)
        try:
            self.url = None
            self.image_url = None
            self.source_name = None

            label = os.path.dirname(file).replace('_', '__') if file else None
            info = Util.read_metadata(file) if file else None
            if info and "sourceURL" in info and "sourceName" in info:
                self.source_name = info["sourceName"]
                if "Fetched" in self.source_name:
                    self.source_name = None
                    label = _("Fetched: Show Origin")
                else:
                    label = _("View at %s") % self.source_name

                self.url = info["sourceURL"]
                if self.url.startswith('//'):
                    self.url = 'https:' + self.url

                if "imageURL" in info:
                    self.image_url = info["imageURL"]
                    if self.image_url.startswith('//'):
                        self.image_url = self.url.split('//')[0] + self.image_url

            if label and len(label) > 50:
                label = label[:50] + "..."

            author = None
            if info and "author" in info and "authorURL" in info:
                author = info["author"]
                if len(author) > 50:
                    author = author[:50] + "..."
                self.author_url = info["authorURL"]
            else:
                self.author_url = None

            if not self.ind:
                return

            deleteable = bool(file) and os.access(file, os.W_OK) and not self.is_current_refreshable()
            favs_op = self.determine_favorites_operation(file)
            image_source = self.get_source(file)

            if not is_gtk_thread:
                Gdk.threads_enter()

            try:
                rating_menu = None
                if deleteable:
                    rating_menu = ThumbsManager.create_rating_menu(file, self)

                quote_not_fav = True
                if self.options.quotes_enabled and self.quote is not None:
                    quote_not_fav = self.quote is not None and self.quote_favorites_contents.find(self.current_quote_to_text()) == -1

                for i in xrange(5):    # if only done once, the menu is not always updated for some reason
                    self.ind.prev.set_sensitive(self.position < len(self.used) - 1)
                    if getattr(self.ind, 'prev_main', None):
                        self.ind.prev_main.set_sensitive(self.position < len(self.used) - 1)
                    self.ind.fast_forward.set_sensitive(self.position > 0)

                    self.ind.file_label.set_visible(bool(file))
                    self.ind.file_label.set_sensitive(bool(file))
                    self.ind.file_label.set_label(os.path.basename(file).replace('_', '__') if file else _("Unknown"))

                    self.ind.focus.set_sensitive(image_source is not None)

                    # delay enabling Trash if auto_changed
                    self.ind.trash.set_visible(bool(file))
                    self.ind.trash.set_sensitive(deleteable and not auto_changed)

                    self.ind.sfw_menu_item.set_visible(self.url is not None)
                    if hasattr(self.ind, 'safe_mode'):
                        self.ind.safe_mode.handler_block(self.ind.safe_mode_handler_id)
                        self.ind.safe_mode.set_active(self.options.safe_mode)
                        self.ind.safe_mode.set_label(_('Safe mode: On') if self.options.safe_mode else _('Turn Safe mode on'))
                        self.ind.safe_mode.handler_unblock(self.ind.safe_mode_handler_id)
                    if hasattr(self.ind, 'rating_items'):
                        for item in self.ind.rating_items:
                            item.set_sensitive(self.url is not None)

                    self.update_favorites_menuitems(self.ind, auto_changed, favs_op)

                    self.ind.show_origin.set_visible(bool(label))
                    self.ind.show_origin.set_sensitive(True)
                    if label:
                        self.ind.show_origin.set_label(label)

                    if not author:
                        self.ind.show_author.set_visible(False)
                        self.ind.show_author.set_sensitive(False)
                    else:
                        self.ind.show_author.set_visible(True)
                        self.ind.show_author.set_sensitive(True)
                        self.ind.show_author.set_label(_("Author: %s") % author)

                    self.ind.rating.set_sensitive(rating_menu is not None)
                    if rating_menu:
                        self.ind.rating.set_submenu(rating_menu)

                    self.ind.history.handler_block(self.ind.history_handler_id)
                    self.ind.history.set_active(self.thumbs_manager.is_showing("history"))
                    self.ind.history.handler_unblock(self.ind.history_handler_id)

                    self.ind.downloads.set_visible(self.options.download_enabled)
                    self.ind.downloads.set_sensitive(len(self.downloaded) > 0)
                    self.ind.downloads.handler_block(self.ind.downloads_handler_id)
                    self.ind.downloads.set_active(self.thumbs_manager.is_showing("downloads"))
                    self.ind.downloads.handler_unblock(self.ind.downloads_handler_id)

                    self.ind.selector.handler_block(self.ind.selector_handler_id)
                    self.ind.selector.set_active(self.thumbs_manager.is_showing("selector"))
                    self.ind.selector.handler_unblock(self.ind.selector_handler_id)

                    self.ind.publish_fb.set_sensitive(self.url is not None)
                    self.ind.google_image.set_sensitive(self.image_url is not None)

                    self.ind.pause_resume.set_label(_("Pause on current") if self.options.change_enabled else _("Resume regular changes"))

                    if self.options.quotes_enabled and self.quote is not None:
                        self.ind.quotes.set_visible(True)
                        self.ind.google_quote_author.set_visible(self.quote.get("author", None) is not None)
                        if "sourceName" in self.quote and "link" in self.quote:
                            self.ind.view_quote.set_visible(True)
                            self.ind.view_quote.set_label(_("View at %s") % self.quote["sourceName"])
                        else:
                            self.ind.view_quote.set_visible(False)

                        if self.quotes_engine:
                            self.ind.prev_quote.set_sensitive(self.quotes_engine.has_previous())

                        self.ind.quotes_pause_resume.set_label(_("Pause on current") if self.options.quotes_change_enabled else _("Resume regular changes"))

                        self.ind.quote_favorite.set_sensitive(quote_not_fav)
                        self.ind.quote_favorite.set_label(_("Save to Favorites") if quote_not_fav else _("Already in Favorites"))
                        self.ind.quote_view_favs.set_sensitive(os.path.isfile(self.options.quotes_favorites_file))

                        self.ind.quote_clipboard.set_sensitive(self.quote is not None)

                    else:
                        self.ind.quotes.set_visible(False)

                    no_effects_visible = self.filters or self.options.quotes_enabled or self.options.clock_enabled
                    self.ind.no_effects.set_visible(no_effects_visible)
                    self.ind.no_effects.handler_block(self.ind.no_effects_handler_id)
                    self.ind.no_effects.set_active(self.no_effects_on == file)
                    self.ind.no_effects.handler_unblock(self.ind.no_effects_handler_id)
            finally:
                if not is_gtk_thread:
                    Gdk.threads_leave()

            # delay enabling Move/Copy operations after automatic changes - protect from inadvertent clicks
            if auto_changed:
                def update_file_operations():
                    for i in xrange(5):
                        self.ind.trash.set_sensitive(deleteable)
                        self.ind.copy_to_favorites.set_sensitive(favs_op in ("copy", "both"))
                        self.ind.move_to_favorites.set_sensitive(favs_op in ("move", "both"))
                GObject.timeout_add(2000, update_file_operations)

        except Exception:
            logger.exception(lambda: "Error updating file info")

    def regular_change_thread(self):
        logger.info(lambda: "regular_change thread running")

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
                    wait_more = self.options.change_interval - max(0, (now - self.last_change_time))
                    if self.options.change_enabled:
                        self.change_event.wait(max(0, wait_more))
                    else:
                        logger.info(lambda: "regular_change: waiting till user resumes")
                        self.change_event.wait()
                    self.change_event.clear()
                if not self.running:
                    return
                if not self.options.change_enabled:
                    continue
                logger.info(lambda: "regular_change changes wallpaper")
                self.auto_changed = True
                self.last_change_time = time.time()
                self.change_wallpaper()
            except Exception:
                logger.exception(lambda: "Exception in regular_change_thread")

    def clock_thread_method(self):
        logger.info(lambda: "clock thread running")

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
                    logger.info(lambda: "clock_thread updates wallpaper")
                    self.auto_changed = False
                    self.refresh_clock()
                    last_minute = minute
            except Exception:
                logger.exception(lambda: "Exception in clock_thread")

    def find_images(self):
        self.prepared_cleared = False
        images = self.select_random_images(100 if not self.options.safe_mode else 30)

        found = set()
        for fuzziness in xrange(0, 5):
            if len(found) > 10 or len(found) >= len(images):
                break
            for img in images:
                if not self.running or self.prepared_cleared:
                    # abandon this search
                    return

                try:
                    if not img in found and self.image_ok(img, fuzziness):
                        #print "OK at fz %d: %s" % (fuzziness, img)
                        found.add(img)
                        if len(self.prepared) < 3 and not self.prepared_cleared:
                            with self.prepared_lock:
                                self.prepared.append(img)
                except Exception:
                    logger.exception(lambda: "Excepion while testing image_ok on file " + img)

        with self.prepared_lock:
            if self.prepared_cleared:
                # abandon this search
                return

            self.prepared.extend(found)
            if not self.prepared and images:
                logger.info(lambda: "Prepared buffer still empty after search, appending some non-ok image")
                self.prepared.append(images[random.randint(0, len(images) - 1)])

            # remove duplicates
            self.prepared = list(set(self.prepared))
            random.shuffle(self.prepared)

        if len(images) < 3 and self.has_real_downloaders():
            self.trigger_download()

        if len(found) <= 5 and len(images) >= max(20, 10 * len(found)) and found.issubset(set(self.used[:10])):
            logger.warning(lambda: "Too few images found: %d out of %d" % (len(found), len(images)))
            if not hasattr(self, "filters_warning_shown") or not self.filters_warning_shown:
                self.filters_warning_shown = True
                self.show_notification(
                    _("Filtering too strict?"),
                    _("Variety is finding too few images that match your image filtering criteria"))

    def prepare_thread(self):
        logger.info(lambda: "Prepare thread running")
        while self.running:
            try:
                logger.info(lambda: "Prepared buffer contains %s images" % len(self.prepared))
                if self.image_count < 0 or len(self.prepared) <= min(10, self.image_count // 2):
                    logger.info(lambda: "Preparing some images")
                    self.find_images()
                    if not self.running:
                        return
                    logger.info(lambda: "After search prepared buffer contains %s images" % len(self.prepared))
            except Exception:
                logger.exception(lambda: "Error in prepare thread:")

            self.prepare_event.wait()
            self.prepare_event.clear()

    def server_options_thread(self):
        time.sleep(20)
        attempts = 0
        while self.running:
            try:
                attempts += 1
                logger.info(lambda: "Fetching server options from %s" % VarietyWindow.SERVERSIDE_OPTIONS_URL)
                self.server_options = Util.fetch_json(VarietyWindow.SERVERSIDE_OPTIONS_URL)
                logger.info(lambda: "Fetched server options: %s" % str(self.server_options))
                if self.preferences_dialog:
                    self.preferences_dialog.update_status_message()

                if varietyconfig.get_version() in self.server_options.get('outdated_versions', []):
                    self.show_notification('Version unsupported', OUTDATED_MSG)
                    GObject.idle_add(self.on_quit)
            except Exception:
                logger.exception(lambda: "Could not fetch Variety serverside options")
                if attempts < 5:
                    # the first several attempts may easily fail if Variety is run on startup, try again soon:
                    time.sleep(30)
                    continue

            time.sleep(3600 * 24) # Update once daily

    def reporting_thread_method(self):
        time.sleep(20)
        attempts = 0
        while self.running:
            try:
                attempts += 1
                if self.options.stats_enabled:
                    self.smart.stats_report_config()
            except Exception:
                logger.exception("Stats: Could not report config")
                if attempts < 3:
                    # the first several attempts may easily fail if Variety is run on startup, try again soon:
                    time.sleep(30)
                    continue

            time.sleep(3600 * 6)  # Report once per 6 hours

    def has_real_downloaders(self):
        return sum(1 for d in self.downloaders if not d.is_refresher) > 0

    def download_thread(self):
        self.last_dl_time = time.time()
        while self.running:
            try:
                while not self.options.download_enabled or \
                      (time.time() - self.last_dl_time) < self.options.download_interval:
                    if not self.running:
                        return
                    now = time.time()
                    wait_more = self.options.download_interval - max(0, (now - self.last_dl_time))
                    if self.options.download_enabled:
                        self.dl_event.wait(max(0, wait_more))
                    else:
                        self.dl_event.wait()
                    self.dl_event.clear()

                if not self.running:
                    return
                if not self.options.download_enabled:
                    continue

                self.last_dl_time = time.time()
                if self.downloaders:
                    self.purge_downloaded()

                    # download from a random downloader (gives equal chance to all)
                    downloader = self.downloaders[random.randint(0, len(self.downloaders) - 1)]
                    self.download_one_from(downloader)

                    # Also refresh the images for all the refreshers - these need to be updated regularly
                    for dl in self.downloaders:
                        if dl.is_refresher and dl != downloader:
                            dl.download_one()

            except Exception:
                logger.exception(lambda: "Could not download wallpaper:")

    def trigger_download(self):
        if self.downloaders:
            logger.info(lambda: "Triggering one download")
            self.last_dl_time = 0
            self.dl_event.set()

    def prepare_earth_downloader(self):
        dl = EarthDownloader(self)
        dl.update_download_folder()
        if not os.path.exists(dl.target_folder):
            dl.download_one()

    def register_downloaded_file(self, file):
        if not self.downloaded or self.downloaded[0] != file:
            self.downloaded.insert(0, file)
            self.downloaded = self.downloaded[:100]
            self.refresh_thumbs_downloads(file)

            if file.startswith(self.options.download_folder):
                self.download_folder_size += os.path.getsize(file)

    def download_one_from(self, downloader):
        file = downloader.download_one()
        if file:
            self.register_downloaded_file(file)

            if downloader.is_refresher or self.image_ok(file, 0):
                # give priority to newly-downloaded images - prepared_from_downloads are later prepended to self.prepared
                logger.info(lambda: "Adding downloaded file %s to prepared_from_downloads queue" % file)
                with self.prepared_lock:
                    self.prepared_from_downloads.append(file)
            else:
                # image is not ok, but still notify prepare thread that there is a new image - it might be "desperate"
                self.prepare_event.set()

    def purge_downloaded(self):
        if not self.options.quota_enabled:
            return

        if self.download_folder_size <= 0 or random.randint(0, 20) == 0:
            self.download_folder_size = self.get_folder_size(self.real_download_folder)
            logger.info(lambda: "Refreshed download folder size: %d mb", self.download_folder_size / (1024.0 * 1024.0))

        mb_quota = self.options.quota_size * 1024 * 1024
        if self.download_folder_size > 0.95 * mb_quota:
            logger.info(lambda: "Purging oldest files from download folder %s, current size: %d mb" %
                        (self.real_download_folder, int(self.download_folder_size / (1024.0 * 1024.0))))
            files = []
            for dirpath, dirnames, filenames in os.walk(self.real_download_folder):
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
                        logger.debug(lambda: "Deleting old file in downloaded: " + file)
                        self.remove_from_queues(file)
                        os.unlink(file)
                        self.download_folder_size -= files[i][1]
                        try:
                            os.unlink(file + '.metadata.json')
                        except Exception:
                            pass
                        try:
                            os.unlink(file + '.txt')
                        except Exception:
                            pass
                    except Exception:
                        logger.exception(lambda: "Could not delete some file while purging download folder: " + file)
                i += 1
            self.prepare_event.set()

    @staticmethod
    def get_folder_size(start_path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    class RefreshLevel:
        ALL = 0
        FILTERS_AND_TEXTS = 1
        TEXTS = 2
        CLOCK_ONLY = 3

    def set_wp_throttled(self, filename, refresh_level=RefreshLevel.ALL):
        if not filename:
            logger.warning(lambda: 'set_wp_throttled: No wallpaper to set')
            return

        self.thumbs_manager.mark_active(file=filename, position=self.position)

        def _do_set_wp():
            self.do_set_wp(filename, refresh_level)
        threading.Timer(0, _do_set_wp).start()

    def build_imagemagick_filter_cmd(self, filename, target_file):
        if not self.filters:
            return None

        filter = random.choice(self.filters).strip()
        if not filter:
            return None

        w = Gdk.Screen.get_default().get_width()
        h = Gdk.Screen.get_default().get_height()
        cmd = 'convert "%s" -scale %dx%d^ ' % (filename, w, h)

        logger.info(lambda: "Applying filter: " + filter)
        cmd += filter + ' '

        cmd = cmd + ' "' + target_file + '"'
        cmd = cmd.replace("%FILEPATH%", filename)
        cmd = cmd.replace("%FILENAME%", os.path.basename(filename))

        logger.info(lambda: "ImageMagick filter cmd: " + cmd)
        return cmd.encode('utf-8')

    def build_imagemagick_clock_cmd(self, filename, target_file):
        if not (self.options.clock_enabled and self.options.clock_filter.strip()):
            return None

        w = Gdk.Screen.get_default().get_width()
        h = Gdk.Screen.get_default().get_height()
        cmd = 'convert "%s" -scale %dx%d^ ' % (filename, w, h)

        hoffset, voffset = Util.compute_trimmed_offsets(Util.get_size(filename), (w, h))
        clock_filter = self.options.clock_filter
        clock_filter = VarietyWindow.replace_clock_filter_offsets(clock_filter, hoffset, voffset)
        clock_filter = self.replace_clock_filter_fonts(clock_filter)

        # Note: time.strftime does not support Unicode format, so the encode/decode cycle
        clock_filter = time.strftime(clock_filter.encode('utf8'), time.localtime()).decode('utf8') # this should always be called last
        logger.info(lambda: "Applying clock filter: " + clock_filter)

        cmd += clock_filter + u' "' + target_file + '"'
        logger.info(lambda: "ImageMagick clock cmd: " + cmd)
        return cmd.encode('utf-8')

    def replace_clock_filter_fonts(self, clock_filter):
        clock_font_name, clock_font_size = Util.gtk_to_fcmatch_font(self.options.clock_font)
        date_font_name, date_font_size = Util.gtk_to_fcmatch_font(self.options.clock_date_font)
        clock_filter = clock_filter.replace("%CLOCK_FONT_NAME", clock_font_name)
        clock_filter = clock_filter.replace("%CLOCK_FONT_SIZE", clock_font_size)
        clock_filter = clock_filter.replace("%DATE_FONT_NAME", date_font_name)
        clock_filter = clock_filter.replace("%DATE_FONT_SIZE", date_font_size)
        return clock_filter

    @staticmethod
    def replace_clock_filter_offsets(filter, hoffset, voffset):
        def hrepl(m): return str(hoffset + int(m.group(1)))
        def vrepl(m): return str(voffset + int(m.group(1)))
        filter = re.sub(r"\[\%HOFFSET\+(\d+)\]", hrepl, filter)
        filter = re.sub(r"\[\%VOFFSET\+(\d+)\]", vrepl, filter)
        return filter

    def refresh_wallpaper(self):
        self.set_wp_throttled(self.current, refresh_level=VarietyWindow.RefreshLevel.FILTERS_AND_TEXTS)

    def refresh_clock(self):
        self.set_wp_throttled(self.current, refresh_level=VarietyWindow.RefreshLevel.CLOCK_ONLY)

    def refresh_texts(self):
        self.set_wp_throttled(self.current, refresh_level=VarietyWindow.RefreshLevel.TEXTS)

    def write_filtered_wallpaper_origin(self, filename):
        if not filename:
            return
        try:
            with io.open(os.path.join(self.wallpaper_folder, "wallpaper.jpg.txt"), "w", encoding='utf8') as f:
                f.write(_u(filename))
        except Exception:
            logger.exception(lambda: "Cannot write wallpaper.jpg.txt")

    def apply_filters(self, to_set, refresh_level):
        try:
            if self.filters:
                # don't run the filter command when the refresh level is clock or quotes only,
                # use the previous filtered image otherwise
                if refresh_level in [VarietyWindow.RefreshLevel.ALL, VarietyWindow.RefreshLevel.FILTERS_AND_TEXTS]\
                or not self.post_filter_filename:
                    self.post_filter_filename = to_set
                    target_file = os.path.join(self.wallpaper_folder, "wallpaper-filter-%s.jpg" % Util.random_hash())
                    cmd = self.build_imagemagick_filter_cmd(to_set, target_file)
                    if cmd:
                        result = os.system(cmd)
                        if result == 0: #success
                            to_set = target_file
                            self.post_filter_filename = to_set
                        else:
                            logger.warning(lambda:
                                "Could not execute filter convert command. " \
                                "Missing ImageMagick or bad filter defined? Resultcode: %d" % result)
                else:
                    to_set = self.post_filter_filename
            return to_set
        except Exception:
            logger.exception(lambda: 'Could not apply filters:')
            return to_set

    def apply_quote(self, to_set):
        try:
            if self.options.quotes_enabled and self.quote:
                quote_outfile = os.path.join(self.wallpaper_folder, "wallpaper-quote-%s.jpg" % Util.random_hash())
                QuoteWriter.write_quote(self.quote["quote"], self.quote.get("author", None), to_set, quote_outfile, self.options)
                to_set = quote_outfile
            return to_set
        except Exception:
            logger.exception(lambda: 'Could not apply quote:')
            return to_set

    def apply_clock(self, to_set):
        try:
            if self.options.clock_enabled:
                target_file = os.path.join(self.wallpaper_folder, "wallpaper-clock-%s.jpg" % Util.random_hash())
                cmd = self.build_imagemagick_clock_cmd(to_set, target_file)
                result = os.system(cmd)
                if result == 0: #success
                    to_set = target_file
                else:
                    logger.warning(lambda:
                        "Could not execute clock convert command. " \
                        "Missing ImageMagick or bad filter defined? Resultcode: %d" % result)
            return to_set
        except Exception:
            logger.exception(lambda: 'Could not apply clock:')
            return to_set

    def apply_copyto_operation(self, to_set):
        if self.options.copyto_enabled:
            folder = self.get_actual_copyto_folder()
            target_file = os.path.join(folder, "variety-copied-wallpaper-%s.jpg" % Util.random_hash())
            self.cleanup_old_wallpapers(folder, "variety-copied-wallpaper")
            try:
                shutil.copy(to_set, target_file)
                os.chmod(target_file, 0o644) # Read permissions for everyone, write - for the current user
                to_set = target_file
            except Exception:
                logger.exception(lambda:
                    "Could not copy file %s to copyto folder %s. "\
                    "Using it from original locations, so LightDM might not be able to use it." % (to_set, folder))
        return to_set

    def get_actual_copyto_folder(self, option=None):
        option = option or self.options.copyto_folder
        if option == "Default":
            return Util.get_xdg_pictures_folder() if not Util.is_home_encrypted() else "/usr/share/backgrounds"
        else:
            return os.path.normpath(option)

    @throttle(seconds=1, trailing_call=True)
    def do_set_wp(self, filename, refresh_level=RefreshLevel.ALL):
        logger.info(lambda: "Calling do_set_wp with %s, time: %s" % (filename, time.time()))
        with self.do_set_wp_lock:
            try:
                if not os.access(filename, os.R_OK):
                    logger.info(lambda: "Missing file or bad permissions, will not use it: " + filename)
                    return

                if Util.check_and_update_metadata(filename):
                    self.update_images_metadata(os.path.dirname(filename))

                self.write_filtered_wallpaper_origin(filename)
                to_set = filename

                if filename != self.no_effects_on:
                    self.no_effects_on = None
                    to_set = self.apply_filters(to_set, refresh_level)
                    to_set = self.apply_quote(to_set)
                    to_set = self.apply_clock(to_set)
                to_set = self.apply_copyto_operation(to_set)

                self.cleanup_old_wallpapers(self.wallpaper_folder, "wallpaper-", to_set)
                self.update_indicator(filename, is_gtk_thread=False)
                self.set_desktop_wallpaper(to_set, filename, refresh_level)
                self.current = filename

                if self.options.icon == "Current" and self.current:
                    def _set_icon_to_current():
                        if self.ind:
                            self.ind.set_icon(self.current)
                    GObject.idle_add(_set_icon_to_current)

                if refresh_level == VarietyWindow.RefreshLevel.ALL:
                    self.last_change_time = time.time()
                    self.save_last_change_time()
                    self.save_history()
            except Exception:
                logger.exception(lambda: "Error while setting wallpaper")

    def list_images(self):
        return Util.list_files(self.individual_images, self.folders, Util.is_image, max_files=10000)

    def select_random_images(self, count):
        all_images = list(self.list_images())
        self.image_count = len(all_images)
        random.shuffle(all_images)
        return all_images[:count]

    def on_indicator_scroll(self, indicator, steps, direction):
        self.on_indicator_scroll_throttled(indicator, steps, direction)

    @debounce(seconds=0.3)
    def on_indicator_scroll_throttled(self, indicator, steps, direction):
        if direction == Gdk.ScrollDirection.SMOOTH:
            return

        wheel_direction_forward = direction in [Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.LEFT]
        if wheel_direction_forward:
            self.next_wallpaper(widget=self)
        else:
            self.prev_wallpaper(widget=self)

    def prev_wallpaper(self, widget=None):
        self.auto_changed = widget is None
        if self.quotes_engine and self.options.quotes_enabled:
            self.quote = self.quotes_engine.prev_quote()
        if self.position >= len(self.used) - 1:
            return
        else:
            self.position += 1
            self.set_wp_throttled(self.used[self.position])

    def next_wallpaper(self, widget=None, bypass_history=False):
        self.auto_changed = widget is None
        if self.position > 0 and not bypass_history:
            if self.quotes_engine and self.options.quotes_enabled:
                self.quote = self.quotes_engine.next_quote()
            self.position -= 1
            self.set_wp_throttled(self.used[self.position])
        else:
            if bypass_history:
                self.position = 0
                if self.quotes_engine and self.options.quotes_enabled:
                    self.quotes_engine.bypass_history()
            self.change_wallpaper()

    def move_to_history_position(self, position):
        if 0 <= position < len(self.used):
            self.auto_changed = False
            self.position = position
            self.set_wp_throttled(self.used[self.position])
        else:
            logger.warning(lambda: "Invalid position passed to move_to_history_position, %d, used len is %d" % (position, len(self.used)))

    def show_notification(self, title, message="", icon=None, important=False):
        if not icon:
            icon = varietyconfig.get_data_file("media", "variety.svg")

        if not important:
            try:
                self.notification.update(title, message, icon)
            except AttributeError:
                self.notification = Notify.Notification.new(title, message, icon)
            self.notification.set_urgency(Notify.Urgency.LOW)
            self.notification.show()
        else:
            # use a separate notification that will not be updated with a non-important message
            notification = Notify.Notification.new(title, message, icon)
            notification.set_urgency(Notify.Urgency.NORMAL)
            notification.show()

    def change_wallpaper(self, widget=None):
        try:
            img = None

            with self.prepared_lock:
                # prepend the prepared_from_downloads queue and clear it:
                random.shuffle(self.prepared_from_downloads)
                self.prepared[0:0] = self.prepared_from_downloads
                self.prepared_from_downloads = []

                for prep in self.prepared:
                    if prep != self.current and os.access(prep, os.R_OK):
                        img = prep
                        self.prepared.remove(img)
                        self.prepare_event.set()
                        break

            if not img:
                logger.info(lambda: "No images yet in prepared buffer, using some random image")
                self.prepare_event.set()
                rnd_images = self.select_random_images(3)
                rnd_images = [f for f in rnd_images if f != self.current or self.is_current_refreshable()]
                img = rnd_images[0] if rnd_images else None

            if not img:
                logger.info(lambda: "No images found")
                if not self.auto_changed:
                    if self.has_real_downloaders():
                        msg = _("Please add more image sources or wait for some downloads")
                    else:
                        msg = _("Please add more image sources")
                    self.show_notification(_("No more wallpapers"), msg)
                return

            if self.quotes_engine and self.options.quotes_enabled:
                self.quote = self.quotes_engine.change_quote()

            self.set_wallpaper(img, auto_changed=self.auto_changed)
        except Exception:
            logger.exception(lambda: "Could not change wallpaper")

    def set_wallpaper(self, img, auto_changed=False):
        logger.info(lambda: "Calling set_wallpaper with " + img)
        if img == self.current and not self.is_current_refreshable():
            return
        if os.access(img, os.R_OK):
            at_front = self.position == 0
            self.used = self.used[self.position:]
            if len(self.used) == 0 or self.used[0] != img:
                self.used.insert(0, img)
                self.refresh_thumbs_history(img, at_front)

            self.position = 0
            if len(self.used) > 1000:
                self.used = self.used[:1000]
            self.auto_changed = auto_changed
            self.last_change_time = time.time()
            self.set_wp_throttled(img)
        else:
            logger.warning(lambda: "set_wallpaper called with unaccessible image " + img)

    def refresh_thumbs_history(self, added_image, at_front=False):
        if self.thumbs_manager.is_showing("history"):
            def _add():
                if at_front:
                    self.thumbs_manager.add_image(added_image, gdk_thread=False)
                else:
                    self.thumbs_manager.show(self.used[:100], gdk_thread=False, type="history")
                    self.thumbs_manager.pin()
            add_timer = threading.Timer(0, _add)
            add_timer.start()

    def refresh_thumbs_downloads(self, added_image):
        def _update_indicator():
            self.update_indicator(auto_changed=False)
        GObject.idle_add(_update_indicator)

        should_show = self.thumbs_manager.is_showing("downloads") or (
            self.thumbs_manager.get_folders() is not None \
                and sum(1 for f in self.thumbs_manager.get_folders() if Util.file_in(added_image, f)) > 0)

        if should_show:
            def _add():
                self.thumbs_manager.add_image(added_image, gdk_thread=False)
            add_timer = threading.Timer(0, _add)
            add_timer.start()

    def on_rating_changed(self, file):
        with self.prepared_lock:
            self.prepared = [f for f in self.prepared if f != file]
        self.prepare_event.set()
        self.update_indicator(auto_changed=False)

    def image_ok(self, img, fuzziness):
        try:
            if Util.is_animated_gif(img):
                return False

            if self.options.min_rating_enabled:
                rating = Util.get_rating(img)
                if rating is None or rating <= 0 or rating < self.options.min_rating:
                    return False

            if self.options.use_landscape_enabled or self.options.min_size_enabled:
                if img in self.image_colors_cache:
                    width = self.image_colors_cache[img][3]
                    height = self.image_colors_cache[img][4]
                else:
                    i = PILImage.open(img)
                    width = i.size[0]
                    height = i.size[1]

                if not self.size_ok(width, height, fuzziness):
                    return False

            if self.options.desired_color_enabled or self.options.lightness_enabled:
                if not img in self.image_colors_cache:
                    dom = DominantColors(img, False)
                    self.image_colors_cache[img] = dom.get_dominant_colors()
                colors = self.image_colors_cache[img]

                if self.options.lightness_enabled:
                    lightness = colors[2]
                    if self.options.lightness_mode == Options.LightnessMode.DARK:
                        if lightness >= 75 + fuzziness * 6:
                            return False
                    elif self.options.lightness_mode == Options.LightnessMode.LIGHT:
                        if lightness <= 180 - fuzziness * 6:
                            return False
                    else:
                        logger.warning(lambda: "Unknown lightness mode: %d", self.options.lightness_mode)

                if self.options.desired_color_enabled and self.options.desired_color \
                        and not DominantColors.contains_color(colors, self.options.desired_color, fuzziness + 2):
                    return False

            if self.options.safe_mode:
                try:
                    info = Util.read_metadata(img)
                    if info.get('sfwRating', 100) < 100:
                        return False

                    blacklisted = set(k.lower() for k in info.get('keywords', [])) & Smart.get_safe_mode_keyword_blacklist()
                    if len(blacklisted) > 0:
                        return False

                    sfw_rating = Smart.get_sfw_rating(info['sourceURL'])
                    if sfw_rating is not None and sfw_rating < 100:
                        return False
                except Exception:
                    pass

            return True

        except Exception:
            logger.exception(lambda: "Error in image_ok for file %s" % img)
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
        if file:
            subprocess.call(["xdg-open", os.path.dirname(file)])

    def open_file(self, widget=None, file=None):
        if not file:
            file = self.current
        if file:
            subprocess.call(["xdg-open", os.path.realpath(file)])

    def on_show_origin(self, widget=None):
        if self.url:
            logger.info(lambda: "Opening url: " + self.url)
            webbrowser.open_new_tab(self.url)
        else:
            self.open_folder()

    def on_show_author(self, widget=None):
        if hasattr(self, "author_url") and self.author_url:
            logger.info(lambda: "Opening url: " + self.author_url)
            webbrowser.open_new_tab(self.author_url)

    def get_source(self, file = None):
        if not file:
            file = self.current
        if not file:
            return None

        prioritized_sources = []
        prioritized_sources.extend(
            s for s in self.options.sources if s[0] and s[1] == Options.SourceType.IMAGE)
        prioritized_sources.extend(
            s for s in self.options.sources if s[0] and s[1] == Options.SourceType.FOLDER)
        prioritized_sources.extend(
            s for s in self.options.sources if s[0] and s[1] in Options.SourceType.dl_types)
        prioritized_sources.extend(
            s for s in self.options.sources if s[0] and s[1] == Options.SourceType.FETCHED)
        prioritized_sources.extend(
            s for s in self.options.sources if s[0] and s[1] == Options.SourceType.FAVORITES)
        prioritized_sources.extend(
            s for s in self.options.sources if s not in prioritized_sources)

        if len(prioritized_sources) != len(self.options.sources):
            logger.error(lambda: 'len(prioritized_sources) != len(self.options.sources): %d, %d, %s, %s' %
                                 (len(prioritized_sources), len(self.options.sources), prioritized_sources, self.options.sources))

        file_normpath = os.path.normpath(file)
        for s in prioritized_sources:
            try:
                if s[1] == Options.SourceType.IMAGE:
                    if os.path.normpath(s[2]) == file_normpath:
                        return s
                elif file_normpath.startswith(Util.folderpath(self.get_folder_of_source(s))):
                    return s
            except Exception:
                # probably exception while creating the downloader, ignore, continue searching
                pass

        return None

    def focus_in_preferences(self, widget=None, file=None):
        if not file:
            file = self.current
        source = self.get_source(file)
        if source is None:
            self.show_notification(_("Current wallpaper is not in the image sources"))
        else:
            self.on_mnu_preferences_activate()
            self.get_preferences_dialog().focus_source_and_image(source, file)

    def move_or_copy_file(self, file, to, to_name, operation):
        is_move = operation == shutil.move
        try:
            if file != to:
                operation(file, to)
            try:
                operation(file + '.metadata.json', to)
            except Exception:
                pass
            try:
                operation(file + '.txt', to)
            except Exception:
                pass
            logger.info(lambda: ("Moved %s to %s" if is_move else "Copied %s to %s") % (file, to))
            #self.show_notification(("Moved %s to %s" if is_move else "Copied %s to %s") % (os.path.basename(file), to_name))
            return True
        except Exception as err:
            if str(err).find("already exists") > 0:
                if operation == shutil.move:
                    try:
                        os.unlink(file)
                        #self.show_notification(op, op + " " + os.path.basename(file) + " to " + to_name)
                        return True
                    except Exception:
                        logger.exception(lambda: "Cannot unlink " + file)
                else:
                    return True

            logger.exception(lambda: "Could not move/copy to " + to)
            if is_move:
                msg = _("Could not move to %s. You probably don't have permissions to move this file.") % to
            else:
                msg = _("Could not copy to %s. You probably don't have permissions to copy this file.") % to
            dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL, Gtk.MessageType.WARNING, Gtk.ButtonsType.OK, msg)
            self.dialogs.append(dialog)
            dialog.set_title("Move failed" if is_move else "Copy failed")
            dialog.run()
            dialog.destroy()
            self.dialogs.remove(dialog)
            return False

    def move_to_trash(self, widget=None, file=None):
        try:
            if not file:
                file = self.current
            if not file:
                return
            if self.url:
                self.ban_url(self.url)

            if not os.access(file, os.W_OK):
                self.show_notification(
                    _("Cannot delete"),
                    _("You don't have permissions to delete %s to Trash.") % file)
            else:
                if self.current == file:
                    self.next_wallpaper(widget)

                self.remove_from_queues(file)
                self.prepare_event.set()

                self.thumbs_manager.remove_image(file)

                def _go():
                    self.smart.report_file(file, 'trash', async=False)

                    command = 'gvfs-trash "%s" || trash-put "%s" || kfmclient move "%s" trash:/' % (file, file, file)
                    logger.info(lambda: "Running trash command %s" % command)
                    result = os.system(command.encode('utf8'))
                    if result != 0:
                        logger.error(lambda: "Trash resulted in error code %d" % result)
                        self.show_notification(
                            _("Cannot delete"),
                            _("Probably there is no utility for moving to Trash?\nPlease install trash-cli or gvfs-bin or konquerer."))
                threading.Timer(0, _go).start()
        except Exception:
            logger.exception(lambda: "Exception in move_to_trash")

    def ban_url(self, url):
        try:
            self.banned.add(url)
            with io.open(os.path.join(self.config_folder, "banned.txt"), "a", encoding='utf8') as f:
                f.write(_u(url) + "\n")
        except Exception:
            logger.exception(lambda: "Could not ban URL")

    def remove_from_queues(self, file):
        self.position = max(0, self.position - sum(1 for f in self.used[:self.position] if f == file))
        self.used = [f for f in self.used if f != file]
        self.downloaded = [f for f in self.downloaded if f != file]
        with self.prepared_lock:
            self.prepared = [f for f in self.prepared if f != file]

    def remove_folder_from_queues(self, folder):
        self.position = max(0, self.position - sum(1 for f in self.used[:self.position] if Util.file_in(f, folder)))
        self.used = [f for f in self.used if not Util.file_in(f, folder)]
        self.downloaded = [f for f in self.downloaded if not Util.file_in(f, folder)]
        with self.prepared_lock:
            self.prepared = [f for f in self.prepared if not Util.file_in(f, folder)]

    def report_sfw_rating(self, file, rating):
        try:
            if not file:
                file = self.current
            if not file:
                return

            try:
                if self.options.safe_mode and rating <= 50:
                    if self.current == file:
                        self.next_wallpaper(self.ind.rating)
                    self.remove_from_queues(file)
                    self.prepare_event.set()
                    self.thumbs_manager.remove_image(file)
            except:
                logger.exception(lambda: 'Error in report_sfw_rating:')

            Util.write_metadata(file, {'sfwRating': rating})
            self.smart.report_sfw_rating(file, rating, async=True)
            self.show_notification('Thanks for reporting!', 'This makes Variety better for everyone')
        except Exception:
            logger.exception(lambda: "Exception in report_sfw_rating")

    def copy_to_favorites(self, widget=None, file=None):
        try:
            if not file:
                file = self.current
            if not file:
                return
            if os.access(file, os.R_OK) and not self.is_in_favorites(file):
                self.move_or_copy_file(file, self.options.favorites_folder, "favorites", shutil.copy)
                self.update_indicator(auto_changed=False)
                self.smart.report_file(file, 'favorite', async=True)
        except Exception:
            logger.exception(lambda: "Exception in copy_to_favorites")

    def move_to_favorites(self, widget=None, file=None):
        try:
            if not file:
                file = self.current
            if not file:
                return
            if os.access(file, os.R_OK) and not self.is_in_favorites(file):
                operation = shutil.move if os.access(file, os.W_OK) else shutil.copy
                ok = self.move_or_copy_file(file, self.options.favorites_folder, "favorites", operation)
                if ok:
                    new_file = os.path.join(self.options.favorites_folder, os.path.basename(file))
                    self.used = [(new_file if f == file else f) for f in self.used]
                    self.downloaded = [(new_file if f == file else f) for f in self.downloaded]
                    with self.prepared_lock:
                        self.prepared = [(new_file if f == file else f) for f in self.prepared]
                        self.prepare_event.set()
                    if self.current == file:
                        self.current = new_file
                        if self.no_effects_on == file:
                            self.no_effects_on = new_file
                        self.set_wp_throttled(new_file)

                    self.smart.report_file(new_file, 'favorite', async=True)
        except Exception:
            logger.exception(lambda: "Exception in move_to_favorites")

    def determine_favorites_operation(self, file=None):
        if not file:
            file = self.current
        if not file:
            return None

        if self.is_in_favorites(file):
            return "favorite"

        if not os.access(file, os.W_OK):
            return "copy"

        file_normpath = os.path.normpath(file)
        for pair in self.options.favorites_operations:
            folder = pair[0]
            folder_lower = folder.lower().strip()
            if folder_lower == "downloaded":
                folder = self.real_download_folder
            elif folder_lower == "fetched":
                folder = self.options.fetched_folder
            elif folder_lower == "others":
                folder = "/"

            folder = Util.folderpath(folder)

            if file_normpath.startswith(folder):
                op = pair[1].lower().strip()
                return op if op in ("copy", "move", "both") else "copy"

        return "copy"

    def on_quit(self, widget=None):
        logger.info(lambda: "Quitting")
        if self.running:
            self.running = False

            for d in self.dialogs + [self.preferences_dialog, self.about]:
                try:
                    if d:
                        d.destroy()
                except Exception:
                    logger.exception(lambda: "Could not destroy dialog")

            for e in self.events:
                e.set()

            try:
                if self.quotes_engine:
                    self.quotes_engine.quit()
            except Exception:
                logger.exception(lambda: "Could not stop quotes engine")

            if self.options.clock_enabled or self.options.quotes_enabled:
                self.options.clock_enabled = False
                self.options.quotes_enabled = False
                if self.current:
                    GObject.idle_add(lambda: self.do_set_wp(self.current, VarietyWindow.RefreshLevel.TEXTS))

            Util.start_force_exit_thread(15)
            GObject.idle_add(Gtk.main_quit)

    def show_usage_stats_notice(self):
        if not self.options.stats_notice_shown and self.options.stats_enabled:
            self.options.stats_notice_shown = True
            self.options.write()
            self.show_notification(
                _('Anonymous usage statistics'),
                _('Variety collects anonymous usage statistics. \n'
                  'These help us make it better and are not shared with anyone. \n'
                  'To read more or turn them off, go to "Sync and social"'))

    def first_run(self):
        def _go():
            fr_file = os.path.join(self.config_folder, ".firstrun")
            first_run = not os.path.exists(fr_file)
            if first_run:
                self.show_welcome_dialog()
                if not self.running:
                    return

            if not self.options.smart_notice_shown:
                self.smart.show_notice_dialog()
                if not self.running:
                    return

            if first_run:
                with open(fr_file, "w") as f:
                    f.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

            if self.options.smart_enabled and not self.options.smart_register_shown:
                self.smart.show_register_dialog()
                if not self.running:
                    return

            if first_run:
                self.create_autostart_entry()
                self.on_mnu_preferences_activate()
            else:
                self.show_usage_stats_notice()

            self.smart.sync()

        Util.add_mainloop_task(_go)

    def write_current_version(self):
        current_version = varietyconfig.get_version()
        logger.info(lambda: "Writing current version %s to .version" % current_version)
        with open(os.path.join(self.config_folder, ".version"), "w") as f:
            f.write(current_version)

    def update_images_metadata(self, folder=None):
        if getattr(self, 'updating_images_metadata', False):
            return

        def _go():
            if getattr(self, 'updating_images_metadata', False):
                return

            try:
                self.updating_images_metadata = True
                logger.info('Updating images metadata')
                options = Options()
                options.read()

                if not folder:
                    for f in Util.list_files(folders=[options.favorites_folder],
                                             filter_func=Util.is_image, max_files=50000, randomize=True):
                        Util.check_and_update_metadata(f)
                        time.sleep(0.1)

                    for f in Util.list_files(folders=[options.fetched_folder, options.download_folder],
                                             filter_func=Util.is_image, max_files=50000, randomize=True):
                        Util.check_and_update_metadata(f)
                        time.sleep(0.1)
                else:
                    for f in Util.list_files(folders=[folder],
                                             filter_func=Util.is_image, max_files=50000, randomize=True):
                        Util.check_and_update_metadata(f)
                        time.sleep(0.1)

            except Exception:
                logger.exception(lambda: "Could not update images metadata")
            finally:
                self.updating_images_metadata = False

        metadata_thread = threading.Thread(target=_go)
        metadata_thread.daemon = True
        metadata_thread.start()

    def perform_upgrade(self):
        try:
            current_version = varietyconfig.get_version()

            if not os.path.exists(os.path.join(self.config_folder, ".firstrun")):
                # running for the first time
                last_version = current_version
                self.write_current_version()
            else:
                try:
                    with open(os.path.join(self.config_folder, ".version")) as f:
                        last_version = f.read().strip()
                except Exception:
                    last_version = "0.4.12" # this is the last release that did not have the .version file

            logger.info(lambda: "Last run version was %s or earlier, current version is %s" % (last_version, current_version))

            if Util.compare_versions(last_version, "0.4.13") < 0:
                logger.info(lambda: "Performing upgrade to 0.4.13")
                try:
                    # mark the current download folder as a valid download folder
                    options = Options()
                    options.read()
                    logger.info(lambda: "Writing %s to current download folder %s" % (DL_FOLDER_FILE, options.download_folder))
                    Util.makedirs(options.download_folder)
                    dl_folder_file = os.path.join(options.download_folder, DL_FOLDER_FILE)
                    if not os.path.exists(dl_folder_file):
                        with open(dl_folder_file, "w") as f:
                            f.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                except Exception:
                    logger.exception(lambda: "Could not create %s in download folder" % DL_FOLDER_FILE)

            if Util.compare_versions(last_version, "0.4.14") < 0:
                logger.info(lambda: "Performing upgrade to 0.4.14")

                # Current wallpaper is now stored in wallpaper subfolder, remove old artefacts:
                walltxt = os.path.join(self.config_folder, "wallpaper.jpg.txt")
                if os.path.exists(walltxt):
                    try:
                        logger.info(lambda: "Moving %s to %s" % (walltxt, self.wallpaper_folder))
                        shutil.move(walltxt, self.wallpaper_folder)
                    except Exception:
                        logger.exception(lambda: "Could not move wallpaper.jpg.txt")

                for suffix in ("filter", "clock", "quote"):
                    file = os.path.join(self.config_folder, "wallpaper-%s.jpg" % suffix)
                    try:
                        if os.path.exists(file):
                            logger.info(lambda: "Deleting unneeded file " + file)
                            os.unlink(file)
                    except Exception:
                        logger.warning(lambda: "Could not delete %s, no worries" % file)

            # Perform on every upgrade to an newer version:
            if Util.compare_versions(last_version, current_version) < 0:
                self.write_current_version()
                self.update_images_metadata()

                # Upgrade set and get_wallpaper scripts
                def upgrade_script(script, outdated_md5):
                    try:
                        script_file = os.path.join(self.scripts_folder, script)
                        if not os.path.exists(script_file) or Util.md5file(script_file) in outdated_md5:
                            logger.info(lambda: "Outdated %s file, copying it from %s" %
                                        (script, varietyconfig.get_data_file("scripts", script)))
                            shutil.copy(varietyconfig.get_data_file("scripts", script), self.scripts_folder)
                    except Exception:
                        logger.exception(lambda: "Could not upgrade script " + script)

                upgrade_script("set_wallpaper", VarietyWindow.OUTDATED_SET_WP_SCRIPTS)
                upgrade_script("get_wallpaper", VarietyWindow.OUTDATED_GET_WP_SCRIPTS)

                # Upgrade the autostart entry, if there is one
                if os.path.exists(os.path.expanduser(u"~/.config/autostart/variety.desktop")):
                    logger.info(lambda: 'Updating Variety autostart desktop entry')
                    self.create_autostart_entry()

        except Exception:
            logger.exception(lambda: "Error during version upgrade. Continuing.")

    def show_welcome_dialog(self):
        dialog = WelcomeDialog()
        if os.environ.get('KDE_FULL_SESSION') == 'true':
            logger.info(lambda: "KDE detected")
            kde_wp_folder = os.path.join(Util.get_xdg_pictures_folder(), "variety-wallpaper")
            Util.makedirs(kde_wp_folder)
            shutil.copy(varietyconfig.get_data_file("media", "wallpaper-kde.jpg"), kde_wp_folder)
            dialog.ui.kde_warning.set_visible(True)

        def _on_continue(button):
            dialog.destroy()
            self.dialogs.remove(dialog)

        dialog.ui.continue_button.connect("clicked", _on_continue)
        self.dialogs.append(dialog)
        dialog.run()
        dialog.destroy()

    def edit_prefs_file(self, widget=None):
        dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO, Gtk.ButtonsType.OK,
            _("I will open an editor with the config file and apply the changes after you save and close the editor."))
        self.dialogs.append(dialog)
        dialog.set_title("Edit config file")
        dialog.run()
        dialog.destroy()
        self.dialogs.remove(dialog)
        subprocess.call(["gedit", "~/.config/variety/variety.conf"])
        self.reload_config()

    def on_pause_resume(self, widget=None, change_enabled=None):
        if change_enabled is None:
            self.options.change_enabled = not self.options.change_enabled
        else:
            self.options.change_enabled = change_enabled

        if self.preferences_dialog:
            self.preferences_dialog.ui.change_enabled.set_active(self.options.change_enabled)

        self.options.write()
        self.update_indicator(auto_changed=False)
        self.change_event.set()

    def on_safe_mode_toggled(self, widget=None, safe_mode=None):
        if safe_mode is None:
            self.options.safe_mode = not self.options.safe_mode
        else:
            self.options.safe_mode = safe_mode

        if self.preferences_dialog:
            self.preferences_dialog.ui.safe_mode.set_active(self.options.safe_mode)

        self.options.write()
        self.update_indicator(auto_changed=False)
        self.clear_prepared_queue()

    @staticmethod
    def parse_options(arguments, report_errors=True):
        """Support for command line options"""
        usage = _("""%prog [options] [files or urls]

Passing local files will add them to Variety's queue.
Passing remote URLs will make Variety fetch them to Fetched folder and place them in the queue.

To set a specific wallpaper: %prog /some/local/image.jpg --next""")
        parser = VarietyOptionParser(usage=usage, version="%%prog %s" % varietyconfig.get_version(), report_errors=report_errors)

        parser.add_option(
            "-v", "--verbose", action="count", dest="verbose", default=1,
            help=_("Show logging messages (-vv shows even finer debugging messages, -vvv debugs variety_lib too)"))

        parser.add_option(
            "-q", "--quit", action="store_true", dest="quit",
            help=_("Make the running instance quit"))

        parser.add_option(
            "--get", "--current", "--show-current", action="store_true", dest="show_current",
            help=_("Print the current wallpaper location. Used only when the application is already running."))

        parser.add_option(
            "-n", "--next", action="store_true", dest="next",
            help=_("Show Next wallpaper"))

        parser.add_option(
            "-p", "--previous", action="store_true", dest="previous",
            help=_("Show Previous wallpaper"))

        parser.add_option(
            "--fast-forward", action="store_true", dest="fast_forward",
            help=_("Show Next wallpaper, skipping the forward history"))

        parser.add_option(
            "-t", "--trash", action="store_true", dest="trash",
            help=_("Move current wallpaper to Trash. Used only when the application is already running."))

        parser.add_option(
            "-f", "--favorite", action="store_true", dest="favorite",
            help=_("Copy current wallpaper to Favorites. Used only when the application is already running."))

        parser.add_option(
            "--move-to-favorites", action="store_true", dest="movefavorite",
            help=_("Move current wallpaper to Favorites. Used only when the application is already running."))

        parser.add_option(
            "--pause", action="store_true", dest="pause",
            help=_("Pause on current image"))

        parser.add_option(
            "--resume", action="store_true", dest="resume",
            help=_("Resume regular image changes"))

        parser.add_option(
            "--toggle-pause", action="store_true", dest="toggle_pause",
            help=_("Toggle Pause/Resume state"))

        parser.add_option(
            "--quotes-next", action="store_true", dest="quotes_next",
            help=_("Show Next quote"))

        parser.add_option(
            "--quotes-previous", action="store_true", dest="quotes_previous",
            help=_("Show Previous quote"))

        parser.add_option(
            "--quotes-fast-forward", action="store_true", dest="quotes_fast_forward",
            help=_("Show Next quote, skipping the forward history"))

        parser.add_option(
            "--quotes-toggle-pause", action="store_true", dest="quotes_toggle_pause",
            help=_("Toggle Quotes Pause/Resume state"))

        parser.add_option(
            "--quotes-save-favorite", action="store_true", dest="quotes_save_favorite",
            help=_("Save the current quote to Favorites"))

        parser.add_option(
            "--history", action="store_true", dest="history",
            help=_("Toggle History display"))

        parser.add_option(
            "--downloads", action="store_true", dest="downloads",
            help=_("Toggle Recent Downloads display"))

        parser.add_option(
            "--preferences", "--show-preferences", action="store_true", dest="preferences",
            help=_("Show Preferences dialog"))

        parser.add_option(
            "--selector", "--show-selector", action="store_true", dest="selector",
            help=_("Show manual wallpaper selector - the thumbnail bar filled with images from the active image sources"))

        parser.add_option(
            "--set-option", action="append", dest="set_options", nargs=2,
            help=_("Sets and applies an option. "
                   "The option names are the same that are used in Variety's config file ~/.config/variety/variety.conf. "
                   "Multiple options can be set in a single command. "
                   "Example: 'variety --set-option icon Dark --set-option clock_enabled True'. "
                   "USE WITH CAUTION: You are changing the settings file directly in an unguarded way."))

        parser.add_option(
            "--debug-smart", action="store_true", dest="debug_smart",
            help="Debug VRTY.ORG and sync functionality by using local server")

        options, args = parser.parse_args(arguments)

        if report_errors:
            if (options.next or options.fast_forward) and options.previous:
                parser.error(_("options --next/--fast-forward and --previous are mutually exclusive"))

            if options.trash and options.favorite:
                parser.error(_("options --trash and --favorite are mutually exclusive"))

            if options.pause and options.resume:
                parser.error(_("options --pause and --resume are mutually exclusive"))

            if (options.quotes_next or options.quotes_fast_forward) and options.quotes_previous:
                parser.error(_("options --quotes-next/--quotes-fast-forward and --quotes-previous are mutually exclusive"))

        return options, args

    def process_command(self, arguments, initial_run):
        try:
            arguments = [unicode(arg) for arg in arguments]
            logger.info(lambda: "Received command: " + str(arguments))

            options, args = self.parse_options(arguments, report_errors=False)

            if options.quit:
                self.on_quit()
                return

            if args:
                logger.info(lambda: "Treating free arguments as urls: " + str(args))
                if not initial_run:
                    self.process_urls(args)
                else:
                    def _process_urls():
                        self.process_urls(args)
                    GObject.timeout_add(5000, _process_urls)


            if options.set_options:
                try:
                    Options.set_options(options.set_options)
                    if not initial_run:
                        self.reload_config()
                except Exception:
                    logger.exception(lambda: "Could not read/write configuration:")

            def _process_command():
                if not initial_run:
                    if options.trash:
                        self.move_to_trash()
                    elif options.favorite:
                        self.copy_to_favorites()
                    elif options.movefavorite:
                        self.move_to_favorites()

                if options.fast_forward:
                    self.next_wallpaper(bypass_history=True)
                elif options.next:
                    self.next_wallpaper()
                elif options.previous:
                    self.prev_wallpaper()

                if options.pause:
                    self.on_pause_resume(change_enabled=False)
                elif options.resume:
                    self.on_pause_resume(change_enabled=True)
                elif options.toggle_pause:
                    self.on_pause_resume()

                if options.history:
                    self.show_hide_history()
                if options.downloads:
                    self.show_hide_downloads()
                if options.selector:
                    self.show_hide_wallpaper_selector()
                if options.preferences:
                    self.on_mnu_preferences_activate()

                if options.quotes_fast_forward:
                    self.next_quote(bypass_history=True)
                elif options.quotes_next:
                    self.next_quote()
                elif options.quotes_previous:
                    self.prev_quote()

                if options.quotes_toggle_pause:
                    self.on_quotes_pause_resume()

                if options.quotes_save_favorite:
                    self.quote_save_to_favorites()

            GObject.timeout_add(3000 if initial_run else 1, _process_command)

            return self.current if options.show_current else ""
        except Exception:
            logger.exception(lambda: "Could not process passed command")

    def update_indicator_icon(self):
        if self.options.icon != "None":
            if self.ind is None:
                logger.info(lambda: "Creating indicator")
                self.ind, self.indicator, self.status_icon = indicator.new_application_indicator(self)
            else:
                self.ind.set_visible(True)

            if self.options.icon == "Current":
                self.ind.set_icon(self.current)
            else:
                self.ind.set_icon(self.options.icon)
        else:
            if self.ind is not None:
                self.ind.set_visible(False)

    def process_urls(self, urls, verbose=True):
        def fetch():
            try:
                Util.makedirs(self.options.fetched_folder)

                for url in urls:
                    if not self.running:
                        return

                    if url.startswith(('variety://', 'vrty://')):
                        self.process_variety_url(url)
                        continue

                    is_local = os.path.exists(url)

                    if is_local:
                        if not (os.path.isfile(url) and Util.is_image(url)):
                            self.show_notification(_("Not an image"), url)
                            continue

                        file = url
                        local_name = os.path.basename(file)
                        self.show_notification(_("Added to queue"),
                                               local_name + "\n" + _("Press Next to see it"),
                                               icon=file)
                    else:
                        file = ImageFetcher.fetch(url, self.options.fetched_folder,
                                                  progress_reporter=self.show_notification, verbose=verbose)
                        if file:
                            self.show_notification(_("Fetched"), os.path.basename(file) + "\n" + _("Press Next to see it"), icon=file)

                    if file:
                        self.register_downloaded_file(file)
                        with self.prepared_lock:
                            logger.info(lambda: "Adding fetched file %s to used queue immediately after current file" % file)

                            try:
                                if self.used[self.position] != file and (self.position <= 0 or self.used[self.position - 1] != file):
                                    at_front = self.position == 0
                                    self.used.insert(self.position, file)
                                    self.position += 1
                                    self.thumbs_manager.mark_active(file=self.used[self.position], position=self.position)
                                    self.refresh_thumbs_history(file, at_front)
                            except IndexError:
                                self.used.insert(self.position, file)
                                self.position += 1

            except Exception:
                logger.exception(lambda: "Exception in process_urls")

        fetch_thread = threading.Thread(target=fetch)
        fetch_thread.daemon = True
        fetch_thread.start()

    def process_variety_url(self, url):
        try:
            logger.info(lambda: 'Processing variety url %s' % url)

            # make the url urlparse-friendly:
            url = url.replace('variety://', 'http://')
            url = url.replace('vrty://', 'http://')

            parts = urlparse.urlparse(url)
            command = parts.netloc
            args = urlparse.parse_qs(parts.query)

            if command == 'facebook-auth':
                if hasattr(self, 'facebook_helper') and self.facebook_helper:
                    fragments = urlparse.parse_qs(parts.fragment)
                    args.update(fragments)
                    self.facebook_helper.on_facebook_auth(args)

            elif command == 'add-source':
                source_type = args['type'][0].lower()
                if not source_type in Options.SourceType.str_to_type:
                    self.show_notification(_('Unsupported source type'),
                                           _('Are you running the most recent version of Variety?'))
                    return
                def _add():
                    newly_added = self.preferences_dialog.add_sources(Options.str_to_type(source_type), [args['location'][0]])
                    self.preferences_dialog.delayed_apply()
                    if newly_added == 1:
                        self.show_notification(_('New image source added'))
                    else:
                        self.show_notification(_('Image source already exists, enabling it'))
                GObject.idle_add(_add)

            elif command == 'set-wallpaper':
                if "id" in args:
                    image_data = Util.fetch_json(Smart.API_URL + '/image/' + args["id"][0])
                    image_url, origin_url, source_type, source_location, source_name, extra_metadata = \
                        Smart.extract_fetch_data(image_data)
                else:
                    image_url = args["image_url"][0]
                    origin_url = args["origin_url"][0]
                    source_type = args.get("source_type", [None])[0]
                    source_location = args.get("source_location", [None])[0]
                    source_name = args.get("source_name", [None])[0]
                    extra_metadata = {}

                image = ImageFetcher.fetch(image_url, self.options.fetched_folder,
                                           origin_url=origin_url,
                                           source_type=source_type,
                                           source_location=source_location,
                                           source_name=source_name,
                                           extra_metadata=extra_metadata,
                                           progress_reporter=self.show_notification,
                                           verbose=True)
                if image:
                    self.register_downloaded_file(image)
                    self.show_notification(_("Fetched and applied"), os.path.basename(image), icon=image)
                    self.set_wallpaper(image, False)

            elif command == 'smart-login':
                userid = args["id"][0]
                username = args["username"][0]
                authkey = args["authkey"][0]
                self.smart.process_login_request(userid, username, authkey)

            elif command == 'test-variety-link':
                self.show_notification(_('It works!'), _('Yay, Variety links work. Great!'))


            else:
                self.show_notification(_('Unsupported command'), _('Are you running the most recent version of Variety?'))
        except:
            self.show_notification(_('Could not process the given variety:// URL'),
                                   _('Run with logging enabled to see details'))
            logger.exception(lambda: 'Exception in process_variety_url')

    def get_desktop_wallpaper(self):
        try:
            script = os.path.join(self.scripts_folder, "get_wallpaper")

            file = None

            if os.access(script, os.X_OK):
                logger.debug(lambda: "Running get_wallpaper script")
                try:
                    output = subprocess.check_output(script).strip()
                    if output:
                        file = _u(output)
                except subprocess.CalledProcessError:
                    logger.exception(lambda: "Exception when calling get_wallpaper script")
            else:
                logger.warning(lambda: "get_wallpaper script is missing or not executable: " + script)

            if not file and self.gsettings:
                file = self.gsettings.get_string('picture-uri')

            if not file:
                return None

            if file[0] == file[-1] == "'" or file[0] == file[-1] == '"':
                file = file[1:-1]

            file = file.replace("file://", "")
            return file
        except Exception:
            logger.exception(lambda: "Could not get current wallpaper")
            return None

    def cleanup_old_wallpapers(self, folder, prefix, new_wallpaper=None):
        try:
            current_wallpaper = self.get_desktop_wallpaper()
            for name in os.listdir(folder):
                file = os.path.join(folder, name)
                if file != current_wallpaper and file != new_wallpaper and file != self.post_filter_filename and\
                   name.startswith(prefix) and name.endswith(".jpg"):
                    logger.debug(lambda: "Removing old wallpaper %s" % file)
                    os.unlink(file)
        except Exception:
            logger.exception(lambda: "Cannot remove all old wallpaper files from %s:" % folder)

    def set_desktop_wallpaper(self, wallpaper, original_file, refresh_level):
        script = os.path.join(self.scripts_folder, "set_wallpaper")
        if os.access(script, os.X_OK):
            auto = "manual" if not self.auto_changed else \
                ("auto" if refresh_level == VarietyWindow.RefreshLevel.ALL else "refresh")
            logger.debug(lambda: "Running set_wallpaper script with parameters: %s, %s, %s" % (wallpaper, auto, original_file))
            try:
                subprocess.check_call(["timeout", "--kill-after=5", "10", script, wallpaper, auto, original_file])
            except subprocess.CalledProcessError, e:
                if e.returncode == 124:
                    logger.error(lambda: "Timeout while running set_wallpaper script, killed")
                logger.exception(lambda: "Exception when calling set_wallpaper script: %d" % e.returncode)
        else:
            logger.error(lambda: "set_wallpaper script is missing or not executable: " + script)
            if self.gsettings:
                self.gsettings.set_string('picture-uri', "file://" + wallpaper)
                self.gsettings.apply()

    def show_hide_history(self, widget=None):
        if self.thumbs_manager.is_showing("history"):
            self.thumbs_manager.hide(gdk_thread=True, force=True)
        else:
            self.thumbs_manager.show(self.used[:100], gdk_thread=True, type="history")
            self.thumbs_manager.pin()
        self.update_indicator(auto_changed=False)

    def show_hide_downloads(self, widget=None):
        if self.thumbs_manager.is_showing("downloads"):
            self.thumbs_manager.hide(gdk_thread=True, force=True)
        else:
            self.thumbs_manager.show(self.downloaded[:100], gdk_thread=True, type="downloads")
            self.thumbs_manager.pin()
        self.update_indicator(auto_changed=False)

    def show_hide_wallpaper_selector(self, widget=None):
        pref_dialog = self.get_preferences_dialog()
        if self.thumbs_manager.is_showing("selector"):
            self.thumbs_manager.hide(gdk_thread=True, force=True)
        else:
            rows = [r for r in pref_dialog.ui.sources.get_model() if r[0]]
            def _go():
                pref_dialog.show_thumbs(rows, pin=True, thumbs_type="selector")
            threading.Timer(0, _go).start()


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
                        logger.warning(lambda: "Persisted last_change_time after current time, setting to current time")
                        self.last_change_time = now
                logger.info(lambda: "Change interval >= 6 hours, using persisted last_change_time " + str(self.last_change_time))
                logger.info(lambda: "Still to wait: %d seconds" % max(0, self.options.change_interval - (time.time() - self.last_change_time)))
            except Exception:
                logger.info(lambda: "Could not read last change time, setting it to current time")
                self.last_change_time = now
        else:
            logger.info(lambda: "Change interval < 6 hours, ignore persisted last_change_time, " \
                        "wait initially the whole interval: " + str(self.options.change_interval))

    def save_history(self):
        try:
            start = max(0, self.position - 100) # TODO do we want to remember forward history?
            end = min(self.position + 100, len(self.used))
            to_save = self.used[start:end]
            with io.open(os.path.join(self.config_folder, "history.txt"), "w", encoding='utf8') as f:
                f.write(u"%d\n" % (self.position - start))
                for file in to_save:
                    f.write(file + "\n")
        except Exception:
            logger.exception(lambda: "Could not save history")

    def load_history(self):
        self.used = []
        self.position = 0
        self.no_effects_on = None

        try:
            with io.open(os.path.join(self.config_folder, "history.txt"), "r", encoding='utf8') as f:
                lines = list(f)
            self.position = int(lines[0].strip())
            for i, line in enumerate(lines[1:]):
                if os.access(line.strip(), os.R_OK):
                    self.used.append(line.strip())
                elif i <= self.position:
                    self.position = max(0, self.position - 1)
        except Exception:
            logger.warning(lambda: "Could not load history file, continuing without it, no worries")

        current = self.get_desktop_wallpaper()
        if current:
            if os.path.normpath(os.path.dirname(current)) == os.path.normpath(self.wallpaper_folder) or \
               os.path.basename(current).startswith("variety-copied-wallpaper-"):

                try:
                    with io.open(os.path.join(self.wallpaper_folder, "wallpaper.jpg.txt"), encoding='utf8') as f:
                        current = f.read().strip()
                except Exception:
                    logger.exception(lambda: "Cannot read wallpaper.jpg.txt")

        self.current = current
        if self.current and (self.position >= len(self.used) or current != self.used[self.position]):
            self.used.insert(0, self.current)
            self.position = 0

    def publish_on_facebook(self, widget):
        if not self.url:
            logger.warning(lambda: "publish_on_facebook called with no current URL")
            return

        file = self.current
        if not file:
            return

        link = self.url
        picture = self.image_url
        caption = None
        quote_text = self.get_quote_text_for_publishing()
        if self.source_name:
            caption = self.source_name + ", via Variety Wallpaper Changer"
        else:
            caption = "Via Variety Wallpaper Changer"

        logger.info(lambda: "Publish on FB requested with params %s, %s, %s" % (link, picture, caption))

        message = self.options.facebook_message
        if message == u'<current_quote>':
            message = quote_text

        if self.options.facebook_show_dialog:
            publish_dialog = FacebookPublishDialog()
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file, 200, 100)
            publish_dialog.ui.image.set_from_pixbuf(pixbuf)
            buf = publish_dialog.ui.message.get_buffer()

            def _text_changed(widget=None):
                text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip()
                if self.quote and text == quote_text:
                    publish_dialog.ui.fill_quote.set_sensitive(False)
                    publish_dialog.ui.hide_dialog.set_label(_('Do not ask anymore, always use the current quote'))
                else:
                    publish_dialog.ui.fill_quote.set_sensitive(bool(quote_text))
                    publish_dialog.ui.hide_dialog.set_label(_('Do not ask anymore, always use the text above'))

            buf.connect("changed", _text_changed)

            buf.set_text(message)

            publish_dialog.ui.fill_quote.set_visible(bool(quote_text))
            def _fill_quote(widget=None):
                buf.set_text(quote_text)
            publish_dialog.ui.fill_quote.connect("clicked", _fill_quote)

            self.dialogs.append(publish_dialog)
            response = publish_dialog.run()
            publish_dialog.destroy()
            try:
                self.dialogs.remove(publish_dialog)
            except:
                pass
            if not self.running or response != Gtk.ResponseType.OK:
                return

            message = _u(buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)).strip()
            self.options.facebook_message = u'<current_quote>' if message == _u(quote_text) else message
            self.options.facebook_show_dialog = not publish_dialog.ui.hide_dialog.get_active()
            self.options.write()

        if self.facebook_firstrun():
            return

        def do_publish():
            self.facebook_helper = FacebookHelper(self, token_file=os.path.join(self.config_folder, ".fbtoken"))
            def on_success(fb, action, data):
                self.show_notification(_("Published"), _("You may open your Facebook feed to see the post"), icon=file)
                self.facebook_helper = None
            def on_failure(fb, action, data):
                self.show_notification(_("Could not publish"), str(data), icon=file)
                self.facebook_helper = None

            self.facebook_helper.publish(
                message=message, link=link, picture=picture, caption=caption,
                on_success=on_success, on_failure=on_failure)
        GObject.idle_add(do_publish)

    def get_quote_text_for_publishing(self):
        if not self.quote:
            return ''
        author = ("\n-- " + self.quote["author"]) if self.quote.get("author", None) else ""
        text = (self.quote["quote"] + author).strip().encode('utf8')
        return text

    def publish_quote_on_facebook(self, widget):
        if not self.quote:
            logger.warning(lambda: "publish_quote_on_facebook called with no current quote")
            return

        if self.facebook_firstrun():
            return

        def do_publish():
            self.facebook_helper = FacebookHelper(self, token_file=os.path.join(self.config_folder, ".fbtoken"))
            def on_success(fb, action, data):
                self.show_notification(_("Published"), _("You may open your Facebook feed to see the post"))
                self.facebook_helper = None
            def on_failure(fb, action, data):
                self.show_notification(_("Could not publish"), str(data))
                self.facebook_helper = None

            text = self.get_quote_text_for_publishing()
            self.facebook_helper.publish(message=text, caption="Via Variety Wallpaper Changer",
                on_success=on_success, on_failure=on_failure)

        GObject.idle_add(do_publish)

    def disable_quotes(self, widget=None):
        self.options.quotes_enabled = False
        self.quote = None

        if self.preferences_dialog:
            self.preferences_dialog.ui.quotes_enabled.set_active(False)

        self.options.write()
        self.update_indicator(auto_changed=False)
        if self.quotes_engine:
            self.quotes_engine.stop()

    def facebook_firstrun(self):
        def _cleanup():
            if hasattr(self, "facebook_dialog") and self.facebook_dialog:
                self.facebook_dialog.destroy()
                try:
                    self.dialogs.remove(self.facebook_dialog)
                except Exception:
                    pass
                self.facebook_dialog = None

        first_run_file = os.path.join(self.config_folder, ".fbfirstrun")
        if not os.path.exists(first_run_file):
            if hasattr(self, "facebook_dialog") and self.facebook_dialog:
                self.facebook_dialog.present()
                return True
            else:
                self.facebook_dialog = FacebookFirstRunDialog()
                self.dialogs.append(self.facebook_dialog)
                response = self.facebook_dialog.run()
                if not self.running or response != Gtk.ResponseType.OK:
                    _cleanup()
                    return True
                with open(first_run_file, "w") as f:
                    f.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

        _cleanup()
        return False

    def prev_quote(self, widget=None):
        if self.quotes_engine and self.options.quotes_enabled:
            self.quote = self.quotes_engine.prev_quote()
            GObject.idle_add(self.update_indicator)
            self.refresh_texts()

    def next_quote(self, widget=None, bypass_history=False):
        if self.quotes_engine and self.options.quotes_enabled:
            self.quote = self.quotes_engine.next_quote(bypass_history)
            GObject.idle_add(self.update_indicator)
            self.refresh_texts()

    def quote_copy_to_clipboard(self, widget=None):
        if self.quote:
            text = self.quote["quote"] + " - " + self.quote["author"]
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(text, -1)
            clipboard.store()

    def reload_quote_favorites_contents(self):
        self.quote_favorites_contents = ''
        try:
            if os.path.isfile(self.options.quotes_favorites_file):
                with io.open(self.options.quotes_favorites_file, encoding='utf8') as f:
                    self.quote_favorites_contents = f.read()
        except Exception:
            logger.exception(lambda: "Could not load favorite quotes file %s" % self.options.quotes_favorites_file)
            self.quote_favorites_contents = ''

    def current_quote_to_text(self):
        return self.quote["quote"] + \
               ('\n-- ' + self.quote["author"] if self.quote["author"] else '') + \
               '\n%\n' if self.quote else ''

    def quote_save_to_favorites(self, widget=None):
        if self.quote:
            try:
                self.reload_quote_favorites_contents()
                if self.quote_favorites_contents.find(self.current_quote_to_text()) == -1:
                    with open(self.options.quotes_favorites_file, "a") as f:
                        text = self.current_quote_to_text()
                        f.write(text.encode('utf-8'))
                    self.reload_quote_favorites_contents()
                    self.update_indicator()
                    self.show_notification("Saved", "Saved to %s" % self.options.quotes_favorites_file)
                else:
                    self.show_notification(_("Already in Favorites"))
            except Exception:
                logger.exception(lambda: "Could not save quote to favorites")
                self.show_notification("Oops, something went wrong when trying to save the quote to the favorites file")

    def quote_view_favorites(self, widget=None):
        if os.path.isfile(self.options.quotes_favorites_file):
            subprocess.call(["xdg-open", self.options.quotes_favorites_file])

    def on_quotes_pause_resume(self, widget=None, change_enabled=None):
        if change_enabled is None:
            self.options.quotes_change_enabled = not self.options.quotes_change_enabled
        else:
            self.options.quotes_change_enabled = change_enabled

        if self.preferences_dialog:
            self.preferences_dialog.ui.quotes_change_enabled.set_active(self.options.quotes_change_enabled)

        self.options.write()
        self.update_indicator(auto_changed=False)
        if self.quotes_engine:
            self.quotes_engine.on_options_updated(False)

    def view_quote(self, widget=None):
        if self.quote and self.quote.get("link", None):
            webbrowser.open_new_tab(self.quote["link"])

    def google_quote_text(self, widget=None):
        if self.quote and self.quote["quote"]:
            url = "https://google.com/search?q=" + urllib.quote_plus(self.quote["quote"].encode('utf8'))
            webbrowser.open_new_tab(url)

    def google_quote_author(self, widget=None):
        if self.quote and self.quote["author"]:
            url = "https://google.com/search?q=" + urllib.quote_plus(self.quote["author"].encode('utf8'))
            webbrowser.open_new_tab(url)

    def google_image_search(self, widget=None):
        if self.image_url:
            url = "https://www.google.com/searchbyimage?safe=off&image_url=" + urllib.quote_plus(self.image_url.encode('utf8'))
            webbrowser.open_new_tab(url)

    def toggle_no_effects(self, no_effects):
        self.no_effects_on = self.current if no_effects else None
        self.refresh_wallpaper()

    def create_autostart_entry(self):
        try:
            logger.info(lambda: "Creating autostart entry")

            content = (
                "[Desktop Entry]\n"
                "Name=Variety\n"
                "Comment=Variety Wallpaper Changer\n"
                "Icon=variety\n"
                "Exec=variety\n"
                "Terminal=false\n"
                "Type=Application\n"
                "X-GNOME-Autostart-Delay=20\n"
            )

            Util.makedirs(os.path.expanduser(u"~/.config/autostart/"))

            path = os.path.expanduser(u"~/.config/autostart/variety.desktop")
            with open(path, "w") as f:
                f.write(content)
        except:
            logger.exception(lambda: "Error while creating autostart desktop entry")
            self.show_notification(_("Could not create autostart entry"),
                _("An error occurred while creating the autostart desktop entry\n"
                "Please run from a terminal with the -v flag and try again."))

    def on_start_slideshow(self, widget=None):
        def _go():
            try:
                if self.options.slideshow_mode.lower() != 'window':
                    subprocess.call(['killall', '-9', 'variety-slideshow'])

                args = ["variety-slideshow"]
                args += ['--seconds', str(self.options.slideshow_seconds)]
                args += ['--fade', str(self.options.slideshow_fade)]
                args += ['--zoom', str(self.options.slideshow_zoom)]
                args += ['--pan', str(self.options.slideshow_pan)]
                if ',' in self.options.slideshow_sort_order.lower():
                    sort = self.options.slideshow_sort_order.lower().split(',')[0]
                    order = self.options.slideshow_sort_order.lower().split(',')[1]
                else:
                    sort = self.options.slideshow_sort_order.lower()
                    order = 'asc'
                args += ['--sort', sort]
                args += ['--order', order]
                args += ['--mode', self.options.slideshow_mode.lower()]

                images = []
                folders = []
                if self.options.slideshow_sources_enabled:
                    for source in self.options.sources:
                        if source[0]:
                            type = source[1]
                            location = source[2]

                            if type == Options.SourceType.IMAGE:
                                images.append(location)
                            else:
                                folder = self.get_folder_of_source(source)
                                if folder:
                                    folders.append(folder)

                if self.options.slideshow_favorites_enabled:
                    folders.append(self.options.favorites_folder)
                if self.options.slideshow_downloads_enabled:
                    folders.append(self.options.download_folder)
                if self.options.slideshow_custom_enabled and os.path.isdir(self.options.slideshow_custom_folder):
                    folders.append(self.options.slideshow_custom_folder)

                if not images and not folders:
                    folders.append(self.options.favorites_folder)

                if not list(Util.list_files(files=images, folders=folders, filter_func=Util.is_image, max_files=1, randomize=False)):
                    self.show_notification(_('No images'), _('There are no images in the slideshow folders'))
                    return

                args += images
                args += folders

                if self.options.slideshow_monitor.lower() != 'all':
                    try:
                        args += ['--monitor', str(int(self.options.slideshow_monitor))]
                    except:
                        pass
                    subprocess.Popen(args)
                else:
                    screen = Gdk.Screen.get_default()
                    for i in range(0, screen.get_n_monitors()):
                        new_args = list(args)
                        new_args += ['--monitor', str(i + 1)]
                        subprocess.Popen(new_args)
            except:
                logger.exception('Could not start slideshow:')
        threading.Thread(target=_go).start()

    def fix_ssl_dependencies(self):
        if not self.options.stats_notice_shown:
            return  # Suggest fix after we've dealt with the other onboarding stuff
        if getattr(self, 'ssl_error_shown', False):
            return  # Suggest fixing only once per run
        self.ssl_error_shown = True

        def _disable_wallhaven_sources(notify=True):
            for s in self.options.sources:
                if s[1] in (Options.SourceType.WALLHAVEN,) and s[0]:
                    s[0] = False
                self.options.write()
            if notify:
                self.show_notification(_("Wallhaven image sources disabled"),
                                       _('Please google "Python SNI SSL error" '
                                         'if you want to fix the problem yourself.'))

        def _go():
            dialog = Gtk.MessageDialog(self.preferences_dialog,
                                       Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO)
            dialog.set_markup(_('There are SSL incompatibilities between your version of Python and some https '
                                'sites like Wallhaven. '
                                'You can <a href="https://stackoverflow.com/questions/18578439/using-requests-with-tls-doesnt-give-sni-support/">read more about the issue here</a>.'
                                '\n\nDo you want to install the Python dependencies required to fix this problem? '
                                '\nThis operation will ask for superuser privileges. '))
            dialog.set_title(_('Variety - SSL error. Install dependencies?'))
            dialog.set_default_response(Gtk.ResponseType.YES)
            self.dialogs.append(dialog)
            response = dialog.run()
            dialog.destroy()
            try:
                self.dialogs.remove(dialog)
            except:
                pass
            if response == Gtk.ResponseType.YES:
                def _do_fix():
                    install_log_path = '/var/log/variety_install_ssl_deps.log'
                    working = True

                    def _poll():
                        start = time.time()
                        while working and time.time() - start < 600:    # max 10 minutes of polling
                            try:
                                with open(install_log_path) as f:
                                    if 'Installing' in f.read():
                                        self.show_notification(
                                            _('Installing...'),
                                            _('Installation will take a minute or two. Please be patient. '
                                              'Log file is at %s' % install_log_path))
                                        return
                                    else:
                                        time.sleep(0.3)
                            except:
                                time.sleep(0.3)

                    Util.start_daemon(_poll)

                    try:
                        script = varietyconfig.get_data_file("scripts", "install_ssl_deps.sh")
                        subprocess.check_call(["pkexec", "bash", script])
                        self.show_notification(_('Dependencies were installed. Please restart Variety now.'),
                                               _( 'If SSL errors persist, you will have to google for '
                                                  '"Python SNI SSL error" and seek another solution.'))
                    except Exception:
                        self.show_notification(_('Failure. Wallhaven sources disabled.'),
                                               _('SSL-related dependencies were not installed successfully. '
                                                 'Please see %s or google "Python SNI SSL error" '
                                                 'and seek another solution.') % install_log_path)
                        _disable_wallhaven_sources(notify=False)
                    finally:
                        working = False

                threading.Timer(0, _do_fix).start()
            else:
                _disable_wallhaven_sources()

        Util.add_mainloop_task(_go)

