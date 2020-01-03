# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (c) 2012-2019, Peter Levi <peterlevi@peterlevi.com>
# Copyright (c) 2017-2019, James Lu <james@overdrivenetworks.com>
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
import logging
import os
import random
import re
import shlex
import shutil
import stat
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser

from PIL import Image as PILImage

from jumble.Jumble import Jumble
from variety import indicator
from variety.AboutVarietyDialog import AboutVarietyDialog
from variety.DominantColors import DominantColors
from variety.FlickrDownloader import FlickrDownloader
from variety.ImageFetcher import ImageFetcher
from variety.Options import Options
from variety.plugins.downloaders.ConfigurableImageSource import ConfigurableImageSource
from variety.plugins.downloaders.DefaultDownloader import SAFE_MODE_BLACKLIST
from variety.plugins.downloaders.ImageSource import ImageSource
from variety.plugins.downloaders.SimpleDownloader import SimpleDownloader
from variety.plugins.IVarietyPlugin import IVarietyPlugin
from variety.PreferencesVarietyDialog import PreferencesVarietyDialog
from variety.PrivacyNoticeDialog import PrivacyNoticeDialog
from variety.profile import (
    DEFAULT_PROFILE_PATH,
    get_autostart_file_path,
    get_desktop_file_name,
    get_profile_path,
    get_profile_short_name,
    get_profile_wm_class,
    is_default_profile,
)
from variety.QuotesEngine import QuotesEngine
from variety.QuoteWriter import QuoteWriter
from variety.ThumbsManager import ThumbsManager
from variety.Util import Util, _, debounce, on_gtk, throttle
from variety.VarietyOptionParser import parse_options
from variety.WelcomeDialog import WelcomeDialog
from variety_lib import varietyconfig

# fmt: off
import gi  # isort:skip
gi.require_version("Notify", "0.7")
from gi.repository import Gdk, GdkPixbuf, Gio, GObject, Gtk, Notify  # isort:skip
Notify.init("Variety")
# fmt: on


random.seed()
logger = logging.getLogger("variety")


DL_FOLDER_FILE = ".variety_download_folder"

DONATE_URL = (
    "https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=DHQUELMQRQW46&lc=BG&item_name="
    "Variety%20Wallpaper%20Changer&currency_code=EUR&bn=PP%2dDonationsBF%3abtn_donate_SM%2egif%3aNonHosted"
)

OUTDATED_MSG = "This version of Variety is outdated and unsupported. Please upgrade. Quitting."


class VarietyWindow(Gtk.Window):
    __gtype_name__ = "VarietyWindow"

    SERVERSIDE_OPTIONS_URL = "http://tiny.cc/variety-options-063"

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
        "6005ee48fc9cb48050af6e0e9572e660",  # 0.6.6 (unary operator expected bug; LP: #1722433)
    }

    OUTDATED_GET_WP_SCRIPTS = {
        "d8df22bf24baa87d5231e31027e79ee5",
        "822aee143c6b3f1166e5d0a9c637dd16",  # 0.4.16, 0.4.17
        "367f629e2f24ad8040e46226b18fdc81",  # 0.4.18, 0.4.19
    }

    # How many unseen_downloads max to for every downloader.
    MAX_UNSEEN_PER_DOWNLOADER = 10

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
                self.gsettings = Gio.Settings.new("org.gnome.desktop.background")
            else:
                self.gsettings = None
        except Exception:
            self.gsettings = None

        self.prepare_config_folder()
        self.dialogs = []

        fr_file = os.path.join(self.config_folder, ".firstrun")
        first_run = not os.path.exists(fr_file)

        if first_run:  # Make setup dialogs block so that privacy notice appears
            self.show_welcome_dialog()
            self.show_privacy_dialog()

        self.thumbs_manager = ThumbsManager(self)

        self.quotes_engine = None
        self.quote = None
        self.quote_favorites_contents = ""
        self.clock_thread = None

        self.perform_upgrade()

        self.events = []

        self.prepared = []
        self.prepared_cleared = False
        self.prepared_lock = threading.Lock()

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

        logger.info(lambda: "Using data_path %s" % varietyconfig.get_data_path())
        self.jumble = Jumble(
            [os.path.join(os.path.dirname(__file__), "plugins", "builtin"), self.plugins_folder]
        )

        setattr(self.jumble, "parent", self)
        self.jumble.load()

        self.image_count = -1
        self.image_colors_cache = {}

        self.load_downloader_plugins()
        self.create_downloaders_cache()
        self.reload_config()
        self.load_last_change_time()

        self.update_indicator(auto_changed=False)

        self.start_threads()

        if first_run:
            self.first_run(fr_file)

        def _delayed():
            self.create_preferences_dialog()

            for plugin in self.jumble.get_plugins(clazz=IVarietyPlugin):
                threading.Timer(0, plugin["plugin"].on_variety_start_complete).start()

        GObject.timeout_add(1000, _delayed)

    def on_mnu_about_activate(self, widget, data=None):
        """Display the about box for variety."""
        if self.about is not None:
            logger.debug(lambda: "show existing about_dialog")
            self.about.set_keep_above(True)
            self.about.present()
            self.about.set_keep_above(False)
            self.about.present()
        else:
            logger.debug(lambda: "create new about dialog")
            self.about = AboutVarietyDialog()  # pylint: disable=E1102
            # Set the version on runtime.
            Gtk.AboutDialog.set_version(self.about, varietyconfig.get_version())
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
            logger.debug(lambda: "create new preferences_dialog")
            self.preferences_dialog = PreferencesVarietyDialog(parent=self)  # pylint: disable=E1102

            def _on_preferences_dialog_destroyed(widget, data=None):
                logger.debug(lambda: "on_preferences_dialog_destroyed")
                self.preferences_dialog = None

            self.preferences_dialog.connect("destroy", _on_preferences_dialog_destroyed)

            def _on_preferences_close_button(arg1, arg2):
                self.preferences_dialog.close()
                return True

            self.preferences_dialog.connect("delete_event", _on_preferences_close_button)

    def on_mnu_preferences_activate(self, widget=None, data=None):
        """Display the preferences window for variety."""
        if self.preferences_dialog is not None:
            if self.preferences_dialog.get_visible():
                logger.debug(lambda: "bring to front existing and visible preferences_dialog")
                self.preferences_dialog.set_keep_above(True)
                self.preferences_dialog.present()
                self.preferences_dialog.set_keep_above(False)
            else:
                logger.debug(lambda: "reload and show existing but non-visible preferences_dialog")
                self.preferences_dialog.reload()
                self.preferences_dialog.show()
        else:
            self.create_preferences_dialog()
            self.preferences_dialog.show()
            # destroy command moved into dialog to allow for a help button

        self.preferences_dialog.present()

    def prepare_config_folder(self):
        self.config_folder = get_profile_path()
        Util.makedirs(self.config_folder)

        Util.copy_with_replace(
            varietyconfig.get_data_file("config", "variety.conf"),
            os.path.join(self.config_folder, "variety_latest_default.conf"),
            {DEFAULT_PROFILE_PATH: get_profile_path(expanded=False)},
        )

        if not os.path.exists(os.path.join(self.config_folder, "variety.conf")):
            logger.info(
                lambda: "Missing config file, copying it from "
                + varietyconfig.get_data_file("config", "variety.conf")
            )
            Util.copy_with_replace(
                varietyconfig.get_data_file("config", "variety.conf"),
                os.path.join(self.config_folder, "variety.conf"),
                {DEFAULT_PROFILE_PATH: get_profile_path(expanded=False)},
            )

        if not os.path.exists(os.path.join(self.config_folder, "ui.conf")):
            logger.info(
                lambda: "Missing ui.conf file, copying it from "
                + varietyconfig.get_data_file("config", "ui.conf")
            )
            shutil.copy(varietyconfig.get_data_file("config", "ui.conf"), self.config_folder)

        self.plugins_folder = os.path.join(self.config_folder, "plugins")
        Util.makedirs(self.plugins_folder)

        self.scripts_folder = os.path.join(self.config_folder, "scripts")
        Util.makedirs(self.scripts_folder)

        if not os.path.exists(os.path.join(self.scripts_folder, "set_wallpaper")):
            logger.info(
                lambda: "Missing set_wallpaper file, copying it from "
                + varietyconfig.get_data_file("scripts", "set_wallpaper")
            )
            Util.copy_with_replace(
                varietyconfig.get_data_file("scripts", "set_wallpaper"),
                os.path.join(self.scripts_folder, "set_wallpaper"),
                {DEFAULT_PROFILE_PATH.replace("~", "$HOME"): get_profile_path(expanded=True)},
            )

        if not os.path.exists(os.path.join(self.scripts_folder, "get_wallpaper")):
            logger.info(
                lambda: "Missing get_wallpaper file, copying it from "
                + varietyconfig.get_data_file("scripts", "get_wallpaper")
            )
            Util.copy_with_replace(
                varietyconfig.get_data_file("scripts", "get_wallpaper"),
                os.path.join(self.scripts_folder, "get_wallpaper"),
                {DEFAULT_PROFILE_PATH.replace("~", "$HOME"): get_profile_path(expanded=True)},
            )

        # make all scripts executable:
        for f in os.listdir(self.scripts_folder):
            path = os.path.join(self.scripts_folder, f)
            os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

        self.wallpaper_folder = os.path.join(self.config_folder, "wallpaper")
        Util.makedirs(self.wallpaper_folder)

        self.create_desktop_entry()

    def register_clipboard(self):
        def clipboard_changed(clipboard, event):
            try:
                if not self.options.clipboard_enabled:
                    return

                text = clipboard.wait_for_text()
                logger.debug(lambda: "Clipboard: %s" % text)
                if not text:
                    return

                valid = [
                    url
                    for url in text.split("\n")
                    if ImageFetcher.url_ok(
                        url, self.options.clipboard_use_whitelist, self.options.clipboard_hosts
                    )
                ]

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

    def get_real_download_folder(self):
        subfolder = "Downloaded by Variety"
        dl = self.options.download_folder

        # If chosen folder is within Variety's config folder, or folder's name is "Downloaded by Variety",
        # or folder is missing or it is empty or it has already been used as a download folder, then use it:
        if (
            Util.file_in(dl, self.config_folder)
            or dl.endswith("/%s" % subfolder)
            or dl.endswith("/%s/" % subfolder)
            or not os.path.exists(dl)
            or not os.listdir(dl)
            or os.path.exists(os.path.join(dl, DL_FOLDER_FILE))
        ):
            return dl
        else:
            # In all other cases (i.e. it is an existing user folder with files in it), use a subfolder inside it
            return os.path.join(dl, subfolder)

    def prepare_download_folder(self):
        self.real_download_folder = self.get_real_download_folder()
        Util.makedirs(self.real_download_folder)
        dl_folder_file = os.path.join(self.real_download_folder, DL_FOLDER_FILE)
        if not os.path.exists(dl_folder_file):
            with open(dl_folder_file, "w") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

    def load_downloader_plugins(self):
        Options.IMAGE_SOURCES = [p["plugin"] for p in self.jumble.get_plugins(ImageSource)]
        Options.CONFIGURABLE_IMAGE_SOURCES = [
            p for p in Options.IMAGE_SOURCES if isinstance(p, ConfigurableImageSource)
        ]
        Options.CONFIGURABLE_IMAGE_SOURCES_MAP = {
            s.get_source_type(): s for s in Options.CONFIGURABLE_IMAGE_SOURCES
        }
        Options.SIMPLE_DOWNLOADERS = [
            p for p in Options.IMAGE_SOURCES if isinstance(p, SimpleDownloader)
        ]
        for image_source in Options.IMAGE_SOURCES:
            image_source.activate()
            image_source.set_variety(self)

    def reload_config(self):
        self.previous_options = self.options

        self.options = Options()
        self.options.read()

        self.update_indicator_icon()

        self.prepare_download_folder()

        Util.makedirs(self.options.favorites_folder)
        Util.makedirs(self.options.fetched_folder)

        self.individual_images = [
            os.path.expanduser(s[2])
            for s in self.options.sources
            if s[0] and s[1] == Options.SourceType.IMAGE
        ]

        self.folders = [
            os.path.expanduser(s[2])
            for s in self.options.sources
            if s[0] and s[1] == Options.SourceType.FOLDER
        ]

        if Options.SourceType.FAVORITES in [s[1] for s in self.options.sources if s[0]]:
            self.folders.append(self.options.favorites_folder)

        if Options.SourceType.FETCHED in [s[1] for s in self.options.sources if s[0]]:
            self.folders.append(self.options.fetched_folder)

        self.downloaders = []
        self.download_folder_size = -1

        self.albums = []

        if self.size_options_changed():
            logger.info(lambda: "Size/landscape settings changed - purging downloaders cache")
            self.create_downloaders_cache()

        for s in self.options.sources:
            enabled, type, location = s

            if not enabled:
                continue

            # prepare a cache for albums to avoid walking those folders on every change
            if type in (Options.SourceType.ALBUM_FILENAME, Options.SourceType.ALBUM_DATE):
                images = Util.list_files(folders=(location,), filter_func=Util.is_image)
                if type == Options.SourceType.ALBUM_FILENAME:
                    images = sorted(images)
                elif type == Options.SourceType.ALBUM_DATE:
                    images = sorted(images, key=os.path.getmtime)
                else:
                    raise Exception("Unsupported album type")

                if images:
                    self.albums.append({"path": os.path.normpath(location), "images": images})

                continue

            if type not in self.options.get_downloader_source_types():
                continue

            if location in self.downloaders_cache[type]:
                self.downloaders.append(self.downloaders_cache[type][location])
            else:
                try:
                    logger.info(
                        lambda: "Creating new downloader for type %s, location %s"
                        % (type, location)
                    )
                    dlr = self.create_downloader(type, location)
                    self.downloaders_cache[type][location] = dlr
                    self.downloaders.append(dlr)
                except Exception:
                    logger.exception(
                        lambda: "Could not create Downloader for type %s, location %s"
                        % (type, location)
                    )

        for downloader in Options.SIMPLE_DOWNLOADERS:
            downloader.update_download_folder(self.real_download_folder)

        for downloader in self.downloaders:
            downloader.update_download_folder(self.real_download_folder)
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

        if self.options.quotes_enabled:
            if not self.quotes_engine:
                self.quotes_engine = QuotesEngine(self)
            self.quotes_engine.start()
        else:
            if self.quotes_engine:
                self.quotes_engine.stop()

        if self.quotes_engine:
            self.reload_quote_favorites_contents()
            clear_prepared = (
                self.previous_options is None
                or self.options.quotes_disabled_sources
                != self.previous_options.quotes_disabled_sources
                or self.options.quotes_tags != self.previous_options.quotes_tags
                or self.options.quotes_authors != self.previous_options.quotes_authors
            )
            self.quotes_engine.on_options_updated(clear_prepared=clear_prepared)

        if self.previous_options and (
            self.options.filters != self.previous_options.filters
            or self.options.quotes_enabled != self.previous_options.quotes_enabled
            or self.options.clock_enabled != self.previous_options.clock_enabled
        ):
            self.no_effects_on = None

        self.update_indicator(auto_changed=False)

        if self.previous_options is None or self.options.filters != self.previous_options.filters:
            threading.Timer(0.1, self.refresh_wallpaper).start()
        else:
            threading.Timer(0.1, self.refresh_texts).start()

        if self.events:
            for e in self.events:
                e.set()

    def clear_prepared_queue(self):
        self.filters_warning_shown = False
        logger.info(lambda: "Clearing prepared queue")
        with self.prepared_lock:
            self.prepared_cleared = True
            self.prepared = []
            self.prepare_event.set()
        self.image_count = -1

    def should_clear_prepared(self):
        return self.previous_options and (
            [s for s in self.previous_options.sources if s[0]]
            != [s for s in self.options.sources if s[0]]
            or self.filtering_options_changed()
        )

    def filtering_options_changed(self):
        if not self.previous_options:
            return False
        if self.size_options_changed():
            return True
        if self.previous_options.safe_mode != self.options.safe_mode:
            return True
        if (
            self.previous_options.desired_color_enabled != self.options.desired_color_enabled
            or self.previous_options.desired_color != self.options.desired_color
        ):
            return True
        if (
            self.previous_options.lightness_enabled != self.options.lightness_enabled
            or self.previous_options.lightness_mode != self.options.lightness_mode
        ):
            return True
        if (
            self.previous_options.min_rating_enabled != self.options.min_rating_enabled
            or self.previous_options.min_rating != self.options.min_rating
        ):
            return True
        return False

    def size_options_changed(self):
        return self.previous_options and (
            self.previous_options.min_size_enabled != self.options.min_size_enabled
            or self.previous_options.min_size != self.options.min_size
            or self.previous_options.use_landscape_enabled != self.options.use_landscape_enabled
        )

    def create_downloaders_cache(self):
        self.downloaders_cache = {}
        for type in Options.get_downloader_source_types():
            self.downloaders_cache[type] = {}

    def create_downloader(self, type, location):
        if type == Options.SourceType.FLICKR:
            return FlickrDownloader(self, location)
        else:
            for dl in Options.SIMPLE_DOWNLOADERS:
                if dl.get_source_type() == type:
                    return dl
            for source in Options.CONFIGURABLE_IMAGE_SOURCES:
                if source.get_source_type() == type:
                    return source.create_downloader(location)

        raise Exception("Unknown downloader type")

    def get_folder_of_source(self, source):
        type = source[1]
        location = source[2]

        if type == Options.SourceType.IMAGE:
            return None
        elif type in Options.SourceType.LOCAL_PATH_TYPES:
            return location
        elif type == Options.SourceType.FAVORITES:
            return self.options.favorites_folder
        elif type == Options.SourceType.FETCHED:
            return self.options.fetched_folder
        else:
            dlr = self.create_downloader(type, location)
            dlr.update_download_folder(self.real_download_folder)
            return dlr.target_folder

    def delete_files_of_source(self, source):
        folder = self.get_folder_of_source(source)
        if Util.file_in(folder, self.real_download_folder):
            self.remove_folder_from_queues(folder)
            should_repaint = (
                self.thumbs_manager.is_showing("history")
                or self.thumbs_manager.is_showing("downloads")
                or (
                    self.thumbs_manager.get_folders() is not None
                    and folder in self.thumbs_manager.get_folders()
                )
            )

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
            partial = os.path.join(self.config_folder, "banned.txt.partial")
            with open(partial, encoding="utf8") as f:
                for line in f:
                    self.banned.add(line.strip())
            os.rename(partial, os.path.join(self.config_folder, "banned.txt"))
        except Exception:
            logger.info(lambda: "Missing or invalid banned URLs list, no URLs will be banned")

    def start_clock_thread(self):
        if not self.clock_thread and self.options.clock_enabled:
            self.clock_event = threading.Event()
            self.events.append(self.clock_event)
            self.clock_thread = threading.Thread(target=self.clock_thread_method)
            self.clock_thread.daemon = True
            self.clock_thread.start()

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
        return "--refreshable" in self.current

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
            else:  # both
                holder.move_to_favorites.set_label(_("Move to Favorites"))
                holder.copy_to_favorites.set_visible(True)
                holder.move_to_favorites.set_visible(True)

    def update_indicator(self, file=None, auto_changed=None):
        if not file:
            file = self.current
        if auto_changed is None:
            auto_changed = self.auto_changed

        logger.info(lambda: "Setting file info to: %s" % file)
        try:
            self.url = None
            self.image_url = None
            self.source_name = None

            label = os.path.dirname(file).replace("_", "__") if file else None
            info = Util.read_metadata(file) if file else None
            if info and "sourceURL" in info and "sourceName" in info:
                self.source_name = info["sourceName"]
                if "Fetched" in self.source_name:
                    self.source_name = None
                    label = _("Fetched: Show Origin")
                elif "noOriginPage" in info:
                    label = _("Source: %s") % self.source_name
                else:
                    label = _("View at %s") % self.source_name

                self.url = info["sourceURL"]
                if self.url.startswith("//"):
                    self.url = "https:" + self.url

                if "imageURL" in info:
                    self.image_url = info["imageURL"]
                    if self.image_url.startswith("//"):
                        self.image_url = self.url.split("//")[0] + self.image_url

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

            deleteable = (
                bool(file) and os.access(file, os.W_OK) and not self.is_current_refreshable()
            )
            favs_op = self.determine_favorites_operation(file)
            image_source = self.get_source(file)

            downloaded = list(
                Util.list_files(
                    files=[],
                    folders=[self.real_download_folder],
                    filter_func=Util.is_image,
                    max_files=1,
                    randomize=False,
                )
            )

            def _gtk_update():
                rating_menu = None
                if deleteable:
                    rating_menu = ThumbsManager.create_rating_menu(file, self)

                quote_not_fav = True
                if self.options.quotes_enabled and self.quote is not None:
                    quote_not_fav = (
                        self.quote is not None
                        and self.quote_favorites_contents.find(self.current_quote_to_text()) == -1
                    )

                for i in range(3):
                    # if only done once, the menu is not always updated for some reason
                    self.ind.prev.set_sensitive(self.position < len(self.used) - 1)
                    if getattr(self.ind, "prev_main", None):
                        self.ind.prev_main.set_sensitive(self.position < len(self.used) - 1)
                    self.ind.fast_forward.set_sensitive(self.position > 0)

                    self.ind.file_label.set_visible(bool(file))
                    self.ind.file_label.set_sensitive(bool(file))
                    self.ind.file_label.set_label(
                        os.path.basename(file).replace("_", "__") if file else _("Unknown")
                    )

                    self.ind.focus.set_sensitive(image_source is not None)

                    # delay enabling Trash if auto_changed
                    self.ind.trash.set_visible(bool(file))
                    self.ind.trash.set_sensitive(deleteable and not auto_changed)

                    self.update_favorites_menuitems(self.ind, auto_changed, favs_op)

                    self.ind.show_origin.set_visible(bool(label))
                    self.ind.show_origin.set_sensitive("noOriginPage" not in info)
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

                    self.ind.downloads.set_visible(len(self.downloaders) > 0)
                    self.ind.downloads.set_sensitive(len(downloaded) > 0)
                    self.ind.downloads.handler_block(self.ind.downloads_handler_id)
                    self.ind.downloads.set_active(self.thumbs_manager.is_showing("downloads"))
                    self.ind.downloads.handler_unblock(self.ind.downloads_handler_id)

                    self.ind.selector.handler_block(self.ind.selector_handler_id)
                    self.ind.selector.set_active(self.thumbs_manager.is_showing("selector"))
                    self.ind.selector.handler_unblock(self.ind.selector_handler_id)

                    self.ind.google_image.set_sensitive(self.image_url is not None)

                    self.ind.pause_resume.set_label(
                        _("Pause on current")
                        if self.options.change_enabled
                        else _("Resume regular changes")
                    )

                    if self.options.quotes_enabled and self.quote is not None:
                        self.ind.quotes.set_visible(True)
                        self.ind.google_quote_author.set_visible(
                            self.quote.get("author", None) is not None
                        )
                        if "sourceName" in self.quote and "link" in self.quote:
                            self.ind.view_quote.set_visible(True)
                            self.ind.view_quote.set_label(
                                _("View at %s") % self.quote["sourceName"]
                            )
                        else:
                            self.ind.view_quote.set_visible(False)

                        if self.quotes_engine:
                            self.ind.prev_quote.set_sensitive(self.quotes_engine.has_previous())

                        self.ind.quotes_pause_resume.set_label(
                            _("Pause on current")
                            if self.options.quotes_change_enabled
                            else _("Resume regular changes")
                        )

                        self.ind.quote_favorite.set_sensitive(quote_not_fav)
                        self.ind.quote_favorite.set_label(
                            _("Save to Favorites") if quote_not_fav else _("Already in Favorites")
                        )
                        self.ind.quote_view_favs.set_sensitive(
                            os.path.isfile(self.options.quotes_favorites_file)
                        )

                        self.ind.quote_clipboard.set_sensitive(self.quote is not None)

                    else:
                        self.ind.quotes.set_visible(False)

                    no_effects_visible = (
                        self.filters or self.options.quotes_enabled or self.options.clock_enabled
                    )
                    self.ind.no_effects.set_visible(no_effects_visible)
                    self.ind.no_effects.handler_block(self.ind.no_effects_handler_id)
                    self.ind.no_effects.set_active(self.no_effects_on == file)
                    self.ind.no_effects.handler_unblock(self.ind.no_effects_handler_id)

            Util.add_mainloop_task(_gtk_update)

            # delay enabling Move/Copy operations after automatic changes - protect from inadvertent clicks
            if auto_changed:

                def update_file_operations():
                    for i in range(5):
                        self.ind.trash.set_sensitive(deleteable)
                        self.ind.copy_to_favorites.set_sensitive(favs_op in ("copy", "both"))
                        self.ind.move_to_favorites.set_sensitive(favs_op in ("move", "both"))

                GObject.timeout_add(2000, update_file_operations)

        except Exception:
            logger.exception(lambda: "Error updating file info")

    def regular_change_thread(self):
        logger.info(lambda: "regular_change thread running")

        if self.options.change_on_start:
            self.change_event.wait(5)  # wait for prepare thread to prepare some images first
            self.auto_changed = True
            self.change_wallpaper()

        while self.running:
            try:
                while (
                    not self.options.change_enabled
                    or (time.time() - self.last_change_time) < self.options.change_interval
                ):
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
        for fuzziness in range(0, 5):
            if len(found) > 10 or len(found) >= len(images):
                break
            for img in images:
                if not self.running or self.prepared_cleared:
                    # abandon this search
                    return

                try:
                    if not img in found and self.image_ok(img, fuzziness):
                        # print "OK at fz %d: %s" % (fuzziness, img)
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
                logger.info(
                    lambda: "Prepared buffer still empty after search, appending some non-ok image"
                )
                self.prepared.append(images[random.randint(0, len(images) - 1)])

            # remove duplicates
            self.prepared = list(set(self.prepared))
            random.shuffle(self.prepared)

        if len(images) < 3 and self.has_real_downloaders():
            self.trigger_download()

        if (
            len(found) <= 5
            and len(images) >= max(20, 10 * len(found))
            and found.issubset(set(self.used[:10]))
        ):
            logger.warning(lambda: "Too few images found: %d out of %d" % (len(found), len(images)))
            if not hasattr(self, "filters_warning_shown") or not self.filters_warning_shown:
                self.filters_warning_shown = True
                self.show_notification(
                    _("Filtering too strict?"),
                    _("Variety is finding too few images that match your image filtering criteria"),
                )

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
                    logger.info(
                        lambda: "After search prepared buffer contains %s images"
                        % len(self.prepared)
                    )

                # trigger download after some interval to reduce resource usage while the wallpaper changes
                delay_dl_timer = threading.Timer(2, self.trigger_download)
                delay_dl_timer.daemon = True
                delay_dl_timer.start()
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
                logger.info(
                    lambda: "Fetching server options from %s" % VarietyWindow.SERVERSIDE_OPTIONS_URL
                )
                self.server_options = Util.fetch_json(VarietyWindow.SERVERSIDE_OPTIONS_URL)
                logger.info(lambda: "Fetched server options: %s" % str(self.server_options))
                if self.preferences_dialog:
                    self.preferences_dialog.update_status_message()

                if varietyconfig.get_version() in self.server_options.get("outdated_versions", []):
                    self.show_notification("Version unsupported", OUTDATED_MSG)
                    self.on_quit()
            except Exception:
                logger.exception(lambda: "Could not fetch Variety serverside options")
                if attempts < 5:
                    # the first several attempts may easily fail if Variety is run on startup, try again soon:
                    time.sleep(30)
                    continue

            time.sleep(3600 * 24)  # Update once daily

    def has_real_downloaders(self):
        return sum(1 for d in self.downloaders if not d.is_refresher()) > 0

    def download_thread(self):
        while self.running:
            try:
                available_downloaders = self._available_downloaders()

                if not available_downloaders:
                    self.dl_event.wait(180)
                    self.dl_event.clear()
                    continue

                if random.random() < 0.05:
                    self.purge_downloaded()

                # download from the downloader with the smallest unseen queue
                downloader = sorted(
                    available_downloaders, key=lambda dl: len(dl.state.get("unseen_downloads", []))
                )[0]
                self.download_one_from(downloader)

                # Also refresh the images for all refreshers that haven't downloaded recently -
                # these need to be updated regularly
                for dl in available_downloaders:
                    if dl.is_refresher() and dl != downloader:
                        dl.download_one()

                # give some breathing room between downloads
                time.sleep(1)
            except Exception:
                logger.exception(lambda: "Exception in download_thread:")

    def _available_downloaders(self):
        now = time.time()
        return [
            dl
            for dl in self.downloaders
            if dl.state.get("last_download_failure", 0) < now - 60
            and (not dl.is_refresher() or dl.state.get("last_download_success", 0) < now - 60)
            and len(dl.state.get("unseen_downloads", [])) <= VarietyWindow.MAX_UNSEEN_PER_DOWNLOADER
        ]

    def trigger_download(self):
        logger.info(lambda: "Triggering download thread to check if download needed")
        if getattr(self, "dl_event"):
            self.dl_event.set()

    def register_downloaded_file(self, file):
        self.refresh_thumbs_downloads(file)
        if file.startswith(self.options.download_folder):
            self.download_folder_size += os.path.getsize(file)

    def download_one_from(self, downloader):
        try:
            file = downloader.download_one()
        except:
            logger.exception(lambda: "Could not download wallpaper:")
            file = None

        if file:
            self.register_downloaded_file(file)
            downloader.state["last_download_success"] = time.time()

            if downloader.is_refresher() or self.image_ok(file, 0):
                # give priority to newly-downloaded images - unseen_downloads are later
                # used with priority over self.prepared
                logger.info(lambda: "Adding downloaded file %s to unseen_downloads" % file)
                with self.prepared_lock:
                    unseen = set(downloader.state.get("unseen_downloads", []))
                    unseen.add(file)
                    downloader.state["unseen_downloads"] = [f for f in unseen if os.path.exists(f)]

            else:
                # image is not ok, but still notify prepare thread that there is a new image -
                # it might be "desperate"
                self.prepare_event.set()
        else:
            # register as download failure for this downloader
            downloader.state["last_download_failure"] = time.time()

        downloader.save_state()

    def purge_downloaded(self):
        if not self.options.quota_enabled:
            return

        if self.download_folder_size <= 0 or random.randint(0, 20) == 0:
            self.download_folder_size = Util.get_folder_size(self.real_download_folder)
            logger.info(
                lambda: "Refreshed download folder size: {} mb".format(
                    self.download_folder_size / (1024.0 * 1024.0)
                )
            )

        mb_quota = self.options.quota_size * 1024 * 1024
        if self.download_folder_size > 0.95 * mb_quota:
            logger.info(
                lambda: "Purging oldest files from download folder {}, current size: {} mb".format(
                    self.real_download_folder, int(self.download_folder_size / (1024.0 * 1024.0))
                )
            )
            files = []
            for dirpath, dirnames, filenames in os.walk(self.real_download_folder):
                for f in filenames:
                    if Util.is_image(f) or f.endswith(".partial"):
                        fp = os.path.join(dirpath, f)
                        files.append((fp, os.path.getsize(fp), os.path.getctime(fp)))
            files = sorted(files, key=lambda x: x[2])
            i = 0
            while i < len(files) and self.download_folder_size > 0.80 * mb_quota:
                file = files[i][0]
                if file != self.current:
                    try:
                        logger.debug(lambda: "Deleting old file in downloaded: {}".format(file))
                        self.remove_from_queues(file)
                        Util.safe_unlink(file)
                        self.download_folder_size -= files[i][1]
                        Util.safe_unlink(file + ".metadata.json")
                    except Exception:
                        logger.exception(
                            lambda: "Could not delete some file while purging download folder: {}".format(
                                file
                            )
                        )
                i += 1
            self.prepare_event.set()

    class RefreshLevel:
        ALL = 0
        FILTERS_AND_TEXTS = 1
        TEXTS = 2
        CLOCK_ONLY = 3

    def set_wp_throttled(self, filename, refresh_level=RefreshLevel.ALL):
        if not filename:
            logger.warning(lambda: "set_wp_throttled: No wallpaper to set")
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
        cmd = "convert %s -scale %dx%d^ " % (shlex.quote(filename), w, h)

        logger.info(lambda: "Applying filter: " + filter)
        cmd += filter + " "

        cmd += shlex.quote(target_file)
        cmd = cmd.replace("%FILEPATH%", shlex.quote(filename))
        cmd = cmd.replace("%FILENAME%", shlex.quote(os.path.basename(filename)))

        logger.info(lambda: "ImageMagick filter cmd: " + cmd)
        return cmd.encode("utf-8")

    def build_imagemagick_clock_cmd(self, filename, target_file):
        if not (self.options.clock_enabled and self.options.clock_filter.strip()):
            return None

        w = Gdk.Screen.get_default().get_width()
        h = Gdk.Screen.get_default().get_height()
        cmd = "convert %s -scale %dx%d^ " % (shlex.quote(filename), w, h)

        hoffset, voffset = Util.compute_trimmed_offsets(Util.get_size(filename), (w, h))
        clock_filter = self.options.clock_filter
        clock_filter = VarietyWindow.replace_clock_filter_offsets(clock_filter, hoffset, voffset)
        clock_filter = self.replace_clock_filter_fonts(clock_filter)

        clock_filter = time.strftime(
            clock_filter, time.localtime()
        )  # this should always be called last
        logger.info(lambda: "Applying clock filter: " + clock_filter)

        cmd += clock_filter
        cmd += " "
        cmd += shlex.quote(target_file)
        logger.info(lambda: "ImageMagick clock cmd: " + cmd)
        return cmd.encode("utf-8")

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
        def hrepl(m):
            return str(hoffset + int(m.group(1)))

        def vrepl(m):
            return str(voffset + int(m.group(1)))

        filter = re.sub(r"\[\%HOFFSET\+(\d+)\]", hrepl, filter)
        filter = re.sub(r"\[\%VOFFSET\+(\d+)\]", vrepl, filter)
        return filter

    def refresh_wallpaper(self):
        self.set_wp_throttled(
            self.current, refresh_level=VarietyWindow.RefreshLevel.FILTERS_AND_TEXTS
        )

    def refresh_clock(self):
        self.set_wp_throttled(self.current, refresh_level=VarietyWindow.RefreshLevel.CLOCK_ONLY)

    def refresh_texts(self):
        self.set_wp_throttled(self.current, refresh_level=VarietyWindow.RefreshLevel.TEXTS)

    def write_filtered_wallpaper_origin(self, filename):
        if not filename:
            return
        try:
            with open(
                os.path.join(self.wallpaper_folder, "wallpaper.jpg.txt"), "w", encoding="utf8"
            ) as f:
                f.write(filename)
        except Exception:
            logger.exception(lambda: "Cannot write wallpaper.jpg.txt")

    def apply_filters(self, to_set, refresh_level):
        try:
            if self.filters:
                # don't run the filter command when the refresh level is clock or quotes only,
                # use the previous filtered image otherwise
                if (
                    refresh_level
                    in [
                        VarietyWindow.RefreshLevel.ALL,
                        VarietyWindow.RefreshLevel.FILTERS_AND_TEXTS,
                    ]
                    or not self.post_filter_filename
                ):
                    self.post_filter_filename = to_set
                    target_file = os.path.join(
                        self.wallpaper_folder, "wallpaper-filter-%s.jpg" % Util.random_hash()
                    )
                    cmd = self.build_imagemagick_filter_cmd(to_set, target_file)
                    if cmd:
                        result = os.system(cmd)
                        if result == 0:  # success
                            to_set = target_file
                            self.post_filter_filename = to_set
                        else:
                            logger.warning(
                                lambda: "Could not execute filter convert command. "
                                "Missing ImageMagick or bad filter defined? Resultcode: %d" % result
                            )
                else:
                    to_set = self.post_filter_filename
            return to_set
        except Exception:
            logger.exception(lambda: "Could not apply filters:")
            return to_set

    def apply_quote(self, to_set):
        try:
            if self.options.quotes_enabled and self.quote:
                quote_outfile = os.path.join(
                    self.wallpaper_folder, "wallpaper-quote-%s.jpg" % Util.random_hash()
                )
                QuoteWriter.write_quote(
                    self.quote["quote"],
                    self.quote.get("author", None),
                    to_set,
                    quote_outfile,
                    self.options,
                )
                to_set = quote_outfile
            return to_set
        except Exception:
            logger.exception(lambda: "Could not apply quote:")
            return to_set

    def apply_clock(self, to_set):
        try:
            if self.options.clock_enabled:
                target_file = os.path.join(
                    self.wallpaper_folder, "wallpaper-clock-%s.jpg" % Util.random_hash()
                )
                cmd = self.build_imagemagick_clock_cmd(to_set, target_file)
                result = os.system(cmd)
                if result == 0:  # success
                    to_set = target_file
                else:
                    logger.warning(
                        lambda: "Could not execute clock convert command. "
                        "Missing ImageMagick or bad filter defined? Resultcode: %d" % result
                    )
            return to_set
        except Exception:
            logger.exception(lambda: "Could not apply clock:")
            return to_set

    def apply_copyto_operation(self, to_set):
        if self.options.copyto_enabled:
            folder = self.get_actual_copyto_folder()
            target_file = os.path.join(
                folder, "variety-copied-wallpaper-%s.jpg" % Util.random_hash()
            )
            self.cleanup_old_wallpapers(folder, "variety-copied-wallpaper")
            try:
                shutil.copy(to_set, target_file)
                os.chmod(
                    target_file, 0o644
                )  # Read permissions for everyone, write - for the current user
                to_set = target_file
            except Exception:
                logger.exception(
                    lambda: "Could not copy file %s to copyto folder %s. "
                    "Using it from original locations, so LightDM might not be able to use it."
                    % (to_set, folder)
                )
        return to_set

    def get_actual_copyto_folder(self, option=None):
        option = option or self.options.copyto_folder
        if option == "Default":
            return (
                Util.get_xdg_pictures_folder()
                if not Util.is_home_encrypted()
                else "/usr/share/backgrounds"
            )
        else:
            return os.path.normpath(option)

    @throttle(seconds=1, trailing_call=True)
    def do_set_wp(self, filename, refresh_level=RefreshLevel.ALL):
        logger.info(lambda: "Calling do_set_wp with %s, time: %s" % (filename, time.time()))
        with self.do_set_wp_lock:
            try:
                if not os.access(filename, os.R_OK):
                    logger.info(
                        lambda: "Missing file or bad permissions, will not use it: " + filename
                    )
                    return

                self.write_filtered_wallpaper_origin(filename)
                to_set = filename

                if filename != self.no_effects_on:
                    self.no_effects_on = None
                    to_set = self.apply_filters(to_set, refresh_level)
                    to_set = self.apply_quote(to_set)
                    to_set = self.apply_clock(to_set)
                to_set = self.apply_copyto_operation(to_set)

                self.cleanup_old_wallpapers(self.wallpaper_folder, "wallpaper-", to_set)
                self.update_indicator(filename)
                self.set_desktop_wallpaper(to_set, filename, refresh_level)
                self.current = filename

                if self.options.icon == "Current" and self.current:

                    def _set_icon_to_current():
                        if self.ind:
                            self.ind.set_icon(self.current)

                    Util.add_mainloop_task(_set_icon_to_current)

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

        # add just the first image of each album to the selection,
        # otherwise albums will get an enormous part of the screentime, as they act as
        # "black holes" - once we start them, we stay there until done
        for album in self.albums:
            all_images.append(album["images"][0])

        random.shuffle(all_images)
        return all_images[:count]

    def on_indicator_scroll(self, indicator, steps, direction):
        if direction in (Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.UP):
            self.recent_scroll_actions = getattr(self, "recent_scroll_actions", [])
            self.recent_scroll_actions = [
                a for a in self.recent_scroll_actions if a[0] > time.time() - 0.3
            ]
            self.recent_scroll_actions.append((time.time(), steps, direction))
            count_up = sum(
                a[1] for a in self.recent_scroll_actions if a[2] == Gdk.ScrollDirection.UP
            )
            count_down = sum(
                a[1] for a in self.recent_scroll_actions if a[2] == Gdk.ScrollDirection.DOWN
            )
            self.on_indicator_scroll_throttled(
                Gdk.ScrollDirection.UP if count_up > count_down else Gdk.ScrollDirection.DOWN
            )

    @debounce(seconds=0.3)
    def on_indicator_scroll_throttled(self, direction):
        if direction == Gdk.ScrollDirection.DOWN:
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
            logger.warning(
                lambda: "Invalid position passed to move_to_history_position, %d, used len is %d"
                % (position, len(self.used))
            )

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

    def _has_local_sources(self):
        return (
            sum(1 for s in self.options.sources if s[0] and s[1] in Options.SourceType.LOCAL_TYPES)
            > 0
        )

    def change_wallpaper(self, widget=None):
        try:
            img = None

            # check if current is part of an album, and show next image in the album
            if self.current:
                for album in self.albums:
                    if os.path.normpath(self.current).startswith(album["path"]):
                        index = album["images"].index(self.current)
                        if 0 <= index < len(album["images"]) - 1:
                            img = album["images"][index + 1]
                            break

            if not img:
                with self.prepared_lock:
                    # with some big probability, use one of the unseen_downloads
                    if (
                        random.random() < self.options.download_preference_ratio
                        or not self._has_local_sources()
                    ):
                        enabled_unseen_downloads = self._enabled_unseen_downloads()
                        if enabled_unseen_downloads:
                            unseen = random.choice(list(enabled_unseen_downloads))
                            self.prepared.insert(0, unseen)

                    for prep in self.prepared:
                        if prep != self.current and os.access(prep, os.R_OK):
                            img = prep
                            try:
                                self.prepared.remove(img)
                            except ValueError:
                                pass
                            self.prepare_event.set()
                            break

            if not img:
                logger.info(lambda: "No images yet in prepared buffer, using some random image")
                self.prepare_event.set()
                rnd_images = self.select_random_images(3)
                rnd_images = [
                    f for f in rnd_images if f != self.current or self.is_current_refreshable()
                ]
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

    def _enabled_unseen_downloads(self):
        # collect the unseen_downloads from the currently enabled downloaders:
        enabled_unseen_downloads = set()
        for dl in self.downloaders:
            for file in dl.state.get("unseen_downloads", []):
                if os.path.exists(file):
                    enabled_unseen_downloads.add(file)
        return enabled_unseen_downloads

    def _remove_from_unseen(self, file):
        for dl in self.downloaders:
            unseen = set(dl.state.get("unseen_downloads", []))
            if file in unseen:
                unseen.remove(file)
                dl.state["unseen_downloads"] = [f for f in unseen if os.path.exists(f)]
                dl.save_state()

                # trigger download after some interval to reduce resource usage while the wallpaper changes
                delay_dl_timer = threading.Timer(2, self.trigger_download)
                delay_dl_timer.daemon = True
                delay_dl_timer.start()

    def set_wallpaper(self, img, auto_changed=False):
        logger.info(lambda: "Calling set_wallpaper with " + img)
        if img == self.current and not self.is_current_refreshable():
            return
        if os.access(img, os.R_OK):
            at_front = self.position == 0
            self.used = self.used[self.position :]
            if len(self.used) == 0 or self.used[0] != img:
                self.used.insert(0, img)
                self.refresh_thumbs_history(img, at_front)
            self.position = 0
            if len(self.used) > 1000:
                self.used = self.used[:1000]

            self._remove_from_unseen(img)

            self.auto_changed = auto_changed
            self.last_change_time = time.time()
            self.set_wp_throttled(img)

            # Unsplash API requires that we call their download endpoint
            # when setting the wallpaper, not when queueing it:
            meta = Util.read_metadata(img)
            if meta and "sourceType" in meta:
                for image_source in Options.IMAGE_SOURCES:
                    if image_source.get_source_type() == meta["sourceType"]:

                        def _do_hook():
                            image_source.on_image_set_as_wallpaper(img, meta)

                        threading.Timer(0, _do_hook).start()
        else:
            logger.warning(lambda: "set_wallpaper called with unaccessible image " + img)

    def refresh_thumbs_history(self, added_image, at_front=False):
        if self.thumbs_manager.is_showing("history"):

            def _add():
                if at_front:
                    self.thumbs_manager.add_image(added_image)
                else:
                    self.thumbs_manager.show(self.used, type="history")
                    self.thumbs_manager.pin()

            add_timer = threading.Timer(0, _add)
            add_timer.start()

    def refresh_thumbs_downloads(self, added_image):
        self.update_indicator(auto_changed=False)

        should_show = added_image not in self.thumbs_manager.images and (
            self.thumbs_manager.is_showing("downloads")
            or (
                self.thumbs_manager.get_folders() is not None
                and sum(
                    1 for f in self.thumbs_manager.get_folders() if Util.file_in(added_image, f)
                )
                > 0
            )
        )

        if should_show:

            def _add():
                self.thumbs_manager.add_image(added_image)

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
                        logger.warning(
                            lambda: "Unknown lightness mode: %d", self.options.lightness_mode
                        )

                if (
                    self.options.desired_color_enabled
                    and self.options.desired_color
                    and not DominantColors.contains_color(
                        colors, self.options.desired_color, fuzziness + 2
                    )
                ):
                    return False

            if self.options.safe_mode:
                try:
                    info = Util.read_metadata(img)
                    if info.get("sfwRating", 100) < 100:
                        return False

                    blacklisted = (
                        set(k.lower() for k in info.get("keywords", [])) & SAFE_MODE_BLACKLIST
                    )
                    if len(blacklisted) > 0:
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
            subprocess.Popen(["xdg-open", os.path.dirname(file)])

    def open_file(self, widget=None, file=None):
        if not file:
            file = self.current
        if file:
            subprocess.Popen(["xdg-open", os.path.realpath(file)])

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

    def get_source(self, file=None):
        if not file:
            file = self.current
        if not file:
            return None

        prioritized_sources = []
        prioritized_sources.extend(
            s for s in self.options.sources if s[0] and s[1] == Options.SourceType.IMAGE
        )
        prioritized_sources.extend(
            s for s in self.options.sources if s[0] and s[1] == Options.SourceType.FOLDER
        )
        prioritized_sources.extend(
            s
            for s in self.options.sources
            if s[0] and s[1] in Options.get_downloader_source_types()
        )
        prioritized_sources.extend(
            s for s in self.options.sources if s[0] and s[1] == Options.SourceType.FETCHED
        )
        prioritized_sources.extend(
            s for s in self.options.sources if s[0] and s[1] == Options.SourceType.FAVORITES
        )
        prioritized_sources.extend(s for s in self.options.sources if s not in prioritized_sources)

        if len(prioritized_sources) != len(self.options.sources):
            logger.error(
                lambda: "len(prioritized_sources) != len(self.options.sources): %d, %d, %s, %s"
                % (
                    len(prioritized_sources),
                    len(self.options.sources),
                    prioritized_sources,
                    self.options.sources,
                )
            )

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
                operation(file + ".metadata.json", to)
            except Exception:
                pass
            logger.info(lambda: ("Moved %s to %s" if is_move else "Copied %s to %s") % (file, to))
            # self.show_notification(("Moved %s to %s" if is_move else "Copied %s to %s") % (os.path.basename(file), to_name))
            return True
        except Exception as err:
            if str(err).find("already exists") > 0:
                if operation == shutil.move:
                    try:
                        os.unlink(file)
                        # self.show_notification(op, op + " " + os.path.basename(file) + " to " + to_name)
                        return True
                    except Exception:
                        logger.exception(lambda: "Cannot unlink " + file)
                else:
                    return True

            logger.exception(lambda: "Could not move/copy to " + to)
            if is_move:
                msg = (
                    _(
                        "Could not move to %s. You probably don't have permissions to move this file."
                    )
                    % to
                )
            else:
                msg = (
                    _(
                        "Could not copy to %s. You probably don't have permissions to copy this file."
                    )
                    % to
                )
            dialog = Gtk.MessageDialog(
                self, Gtk.DialogFlags.MODAL, Gtk.MessageType.WARNING, Gtk.ButtonsType.OK, msg
            )
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
                    _("You don't have permissions to delete %s to Trash.") % file,
                )
            else:
                if self.current == file:
                    self.next_wallpaper(widget)

                self.remove_from_queues(file)
                self.prepare_event.set()

                self.thumbs_manager.remove_image(file)

                def _go():
                    try:
                        gio_file = Gio.File.new_for_path(file)
                        ok = gio_file.trash()
                    except:
                        logger.exception("Gio.File.trash failed with exception")
                        ok = False

                    if not ok:
                        logger.error("Gio.File.trash failed")
                        self.show_notification(
                            _("Cannot delete"),
                            _("Deleting to trash failed, check variety.log for more information."),
                        )

                Util.add_mainloop_task(_go)
        except Exception:
            logger.exception(lambda: "Exception in move_to_trash")

    def ban_url(self, url):
        try:
            self.banned.add(url)
            with open(os.path.join(self.config_folder, "banned.txt"), "a", encoding="utf8") as f:
                f.write(url + "\n")
        except Exception:
            logger.exception(lambda: "Could not ban URL")

    def remove_from_queues(self, file):
        self.position = max(
            0, self.position - sum(1 for f in self.used[: self.position] if f == file)
        )
        self.used = [f for f in self.used if f != file]
        self._remove_from_unseen(file)
        with self.prepared_lock:
            self.prepared = [f for f in self.prepared if f != file]

    def remove_folder_from_queues(self, folder):
        self.position = max(
            0, self.position - sum(1 for f in self.used[: self.position] if Util.file_in(f, folder))
        )
        self.used = [f for f in self.used if not Util.file_in(f, folder)]
        with self.prepared_lock:
            self.prepared = [f for f in self.prepared if not Util.file_in(f, folder)]

    def copy_to_favorites(self, widget=None, file=None):
        try:
            if not file:
                file = self.current
            if not file:
                return
            if os.access(file, os.R_OK) and not self.is_in_favorites(file):
                self.move_or_copy_file(
                    file, self.options.favorites_folder, "favorites", shutil.copy
                )
                self.update_indicator(auto_changed=False)
                self.report_image_favorited(file)
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
                ok = self.move_or_copy_file(
                    file, self.options.favorites_folder, "favorites", operation
                )
                if ok:
                    new_file = os.path.join(self.options.favorites_folder, os.path.basename(file))
                    self.used = [(new_file if f == file else f) for f in self.used]
                    with self.prepared_lock:
                        self.prepared = [(new_file if f == file else f) for f in self.prepared]
                        self.prepare_event.set()
                    if self.current == file:
                        self.current = new_file
                        if self.no_effects_on == file:
                            self.no_effects_on = new_file
                        self.set_wp_throttled(new_file)
                    self.report_image_favorited(new_file)
        except Exception:
            logger.exception(lambda: "Exception in move_to_favorites")

    def report_image_favorited(self, img):
        meta = Util.read_metadata(img)
        if meta and "sourceType" in meta:
            for image_source in Options.IMAGE_SOURCES:
                if image_source.get_source_type() == meta["sourceType"]:

                    def _do_hook():
                        image_source.on_image_favorited(img, meta)

                    threading.Timer(0, _do_hook).start()

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

    @on_gtk
    def on_quit(self, widget=None):
        logger.info(lambda: "Quitting")
        if self.running:
            self.running = False

            logger.debug(lambda: "Trying to destroy all dialogs")
            for d in self.dialogs + [self.preferences_dialog, self.about]:
                logger.debug(lambda: "Trying to destroy dialog %s" % d)
                try:
                    if d:
                        d.destroy()
                except Exception:
                    logger.exception(lambda: "Could not destroy dialog")

            for e in self.events:
                e.set()

            try:
                if self.quotes_engine:
                    logger.debug(lambda: "Trying to stop quotes engine")
                    self.quotes_engine.quit()
            except Exception:
                logger.exception(lambda: "Could not stop quotes engine")

            if self.options.clock_enabled or self.options.quotes_enabled:
                self.options.clock_enabled = False
                self.options.quotes_enabled = False
                if self.current:
                    logger.debug(lambda: "Cleaning up clock & quotes")
                    Util.add_mainloop_task(
                        lambda: self.do_set_wp(self.current, VarietyWindow.RefreshLevel.TEXTS)
                    )

            Util.start_force_exit_thread(15)
            logger.debug(lambda: "OK, waiting for other loops to finish")
            logger.debug(lambda: "Remaining threads: ")
            for t in threading.enumerate():
                logger.debug(lambda: "%s, %s" % (t.name, getattr(t, "_Thread__target", None)))
            Util.add_mainloop_task(Gtk.main_quit)

    @on_gtk
    def first_run(self, fr_file):
        if not self.running:
            return

        with open(fr_file, "w") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

        self.create_autostart_entry()
        self.on_mnu_preferences_activate()

    def write_current_version(self):
        current_version = varietyconfig.get_version()
        logger.info(lambda: "Writing current version %s to .version" % current_version)
        with open(os.path.join(self.config_folder, ".version"), "w") as f:
            f.write(current_version)

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
                    last_version = (
                        "0.4.12"
                    )  # this is the last release that did not have the .version file

            logger.info(
                lambda: "Last run version was %s or earlier, current version is %s"
                % (last_version, current_version)
            )

            if Util.compare_versions(last_version, "0.4.13") < 0:
                logger.info(lambda: "Performing upgrade to 0.4.13")
                try:
                    # mark the current download folder as a valid download folder
                    options = Options()
                    options.read()
                    logger.info(
                        lambda: "Writing %s to current download folder %s"
                        % (DL_FOLDER_FILE, options.download_folder)
                    )
                    Util.makedirs(options.download_folder)
                    dl_folder_file = os.path.join(options.download_folder, DL_FOLDER_FILE)
                    if not os.path.exists(dl_folder_file):
                        with open(dl_folder_file, "w") as f:
                            f.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                except Exception:
                    logger.exception(
                        lambda: "Could not create %s in download folder" % DL_FOLDER_FILE
                    )

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
                    if os.path.exists(file):
                        logger.info(lambda: "Deleting unneeded file " + file)
                        Util.safe_unlink(file)

            if Util.compare_versions(last_version, "0.8.0") < 0:
                logger.info(lambda: "Performing upgrade to 0.8.0")
                options = Options()
                options.read()
                for source in options.sources:
                    source[2] = source[2].replace("alpha.wallhaven.cc", "wallhaven.cc")
                options.write()

            # Perform on every upgrade to an newer version:
            if Util.compare_versions(last_version, current_version) < 0:
                self.write_current_version()

                # Upgrade set and get_wallpaper scripts
                def upgrade_script(script, outdated_md5):
                    try:
                        script_file = os.path.join(self.scripts_folder, script)
                        if (
                            not os.path.exists(script_file)
                            or Util.md5file(script_file) in outdated_md5
                        ):
                            logger.info(
                                lambda: "Outdated %s file, copying it from %s"
                                % (script, varietyconfig.get_data_file("scripts", script))
                            )
                            shutil.copy(
                                varietyconfig.get_data_file("scripts", script), self.scripts_folder
                            )
                    except Exception:
                        logger.exception(lambda: "Could not upgrade script " + script)

                upgrade_script("set_wallpaper", VarietyWindow.OUTDATED_SET_WP_SCRIPTS)
                upgrade_script("get_wallpaper", VarietyWindow.OUTDATED_GET_WP_SCRIPTS)

                # Upgrade the autostart entry, if there is one
                if os.path.exists(get_autostart_file_path()):
                    logger.info(lambda: "Updating Variety autostart desktop entry")
                    self.create_autostart_entry()

        except Exception:
            logger.exception(lambda: "Error during version upgrade. Continuing.")

    def show_welcome_dialog(self):
        dialog = WelcomeDialog()

        def _on_continue(button):
            dialog.destroy()
            self.dialogs.remove(dialog)

        dialog.ui.continue_button.connect("clicked", _on_continue)
        self.dialogs.append(dialog)
        dialog.run()
        dialog.destroy()

    def show_privacy_dialog(self):
        dialog = PrivacyNoticeDialog()

        def _on_accept(*args):
            dialog.destroy()
            self.dialogs.remove(dialog)

        def _on_close(*args):
            # At this point we shouldn't have much to clean up yet!
            sys.exit(1)

        dialog.ui.accept_button.connect("clicked", _on_accept)
        dialog.ui.reject_button.connect("clicked", _on_close)
        dialog.connect("delete-event", _on_close)
        dialog.ui.accept_button.grab_focus()
        self.dialogs.append(dialog)
        dialog.run()

    def edit_prefs_file(self, widget=None):
        dialog = Gtk.MessageDialog(
            self,
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "I will open an editor with the config file and apply the changes after you save and close the editor."
            ),
        )
        self.dialogs.append(dialog)
        dialog.set_title("Edit config file")
        dialog.run()
        dialog.destroy()
        self.dialogs.remove(dialog)
        subprocess.call(["gedit", os.path.join(self.config_folder, "variety.conf")])
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

    def process_command(self, arguments, initial_run):
        try:
            arguments = [str(arg) for arg in arguments]
            logger.info(lambda: "Received command: " + str(arguments))

            options, args = parse_options(arguments, report_errors=False)

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

                if options.set_wallpaper:
                    self.set_wallpaper(options.set_wallpaper)
                elif options.fast_forward:
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

    @on_gtk
    def update_indicator_icon(self):
        if self.options.icon != "None":
            if self.ind is None:
                logger.info(lambda: "Creating indicator")
                self.ind, self.indicator, self.status_icon = indicator.new_application_indicator(
                    self
                )
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

                    if url.startswith(("variety://", "vrty://")):
                        self.process_variety_url(url)
                        continue

                    is_local = os.path.exists(url)

                    if is_local:
                        if not (os.path.isfile(url) and Util.is_image(url)):
                            self.show_notification(_("Not an image"), url)
                            continue

                        file = url
                        local_name = os.path.basename(file)
                        self.show_notification(
                            _("Added to queue"),
                            local_name + "\n" + _("Press Next to see it"),
                            icon=file,
                        )
                    else:
                        file = ImageFetcher.fetch(
                            url,
                            self.options.fetched_folder,
                            progress_reporter=self.show_notification,
                            verbose=verbose,
                        )
                        if file:
                            self.show_notification(
                                _("Fetched"),
                                os.path.basename(file) + "\n" + _("Press Next to see it"),
                                icon=file,
                            )

                    if file:
                        self.register_downloaded_file(file)
                        with self.prepared_lock:
                            logger.info(
                                lambda: "Adding fetched file %s to used queue immediately after current file"
                                % file
                            )

                            try:
                                if self.used[self.position] != file and (
                                    self.position <= 0 or self.used[self.position - 1] != file
                                ):
                                    at_front = self.position == 0
                                    self.used.insert(self.position, file)
                                    self.position += 1
                                    self.thumbs_manager.mark_active(
                                        file=self.used[self.position], position=self.position
                                    )
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
            logger.info(lambda: "Processing variety url %s" % url)

            # make the url urlparse-friendly:
            url = url.replace("variety://", "http://")
            url = url.replace("vrty://", "http://")

            parts = urllib.parse.urlparse(url)
            command = parts.netloc
            args = urllib.parse.parse_qs(parts.query)

            if command == "add-source":
                source_type = args["type"][0].lower()
                if not source_type in Options.get_all_supported_source_types():
                    self.show_notification(
                        _("Unsupported source type"),
                        _("Are you running the most recent version of Variety?"),
                    )
                    return

                def _add():
                    newly_added = self.preferences_dialog.add_sources(
                        source_type, [args["location"][0]]
                    )
                    self.preferences_dialog.delayed_apply()
                    if newly_added == 1:
                        self.show_notification(_("New image source added"))
                    else:
                        self.show_notification(_("Image source already exists, enabling it"))

                Util.add_mainloop_task(_add)

            elif command == "set-wallpaper":
                image_url = args["image_url"][0]
                origin_url = args["origin_url"][0]
                source_type = args.get("source_type", [None])[0]
                source_location = args.get("source_location", [None])[0]
                source_name = args.get("source_name", [None])[0]
                extra_metadata = {}

                image = ImageFetcher.fetch(
                    image_url,
                    self.options.fetched_folder,
                    origin_url=origin_url,
                    source_type=source_type,
                    source_location=source_location,
                    source_name=source_name,
                    extra_metadata=extra_metadata,
                    progress_reporter=self.show_notification,
                    verbose=True,
                )
                if image:
                    self.register_downloaded_file(image)
                    self.show_notification(
                        _("Fetched and applied"), os.path.basename(image), icon=image
                    )
                    self.set_wallpaper(image, False)

            elif command == "test-variety-link":
                self.show_notification(_("It works!"), _("Yay, Variety links work. Great!"))

            else:
                self.show_notification(
                    _("Unsupported command"),
                    _("Are you running the most recent version of Variety?"),
                )
        except:
            self.show_notification(
                _("Could not process the given variety:// URL"),
                _("Run with logging enabled to see details"),
            )
            logger.exception(lambda: "Exception in process_variety_url")

    def get_desktop_wallpaper(self):
        try:
            script = os.path.join(self.scripts_folder, "get_wallpaper")

            file = None

            if os.access(script, os.X_OK):
                logger.debug(lambda: "Running get_wallpaper script")
                try:
                    output = subprocess.check_output(script).decode().strip()
                    if output:
                        file = output
                except subprocess.CalledProcessError:
                    logger.exception(lambda: "Exception when calling get_wallpaper script")
            else:
                logger.warning(
                    lambda: "get_wallpaper script is missing or not executable: " + script
                )

            if not file and self.gsettings:
                file = self.gsettings.get_string("picture-uri")

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
                if (
                    file != current_wallpaper
                    and file != new_wallpaper
                    and file != self.post_filter_filename
                    and name.startswith(prefix)
                    and name.endswith(".jpg")
                ):
                    logger.debug(lambda: "Removing old wallpaper %s" % file)
                    Util.safe_unlink(file)
        except Exception:
            logger.exception(lambda: "Cannot remove all old wallpaper files from %s:" % folder)

    def set_desktop_wallpaper(self, wallpaper, original_file, refresh_level):
        script = os.path.join(self.scripts_folder, "set_wallpaper")
        if os.access(script, os.X_OK):
            auto = (
                "manual"
                if not self.auto_changed
                else ("auto" if refresh_level == VarietyWindow.RefreshLevel.ALL else "refresh")
            )
            logger.debug(
                lambda: "Running set_wallpaper script with parameters: %s, %s, %s"
                % (wallpaper, auto, original_file)
            )
            try:
                subprocess.check_call(
                    ["timeout", "--kill-after=5", "10", script, wallpaper, auto, original_file]
                )
            except subprocess.CalledProcessError as e:
                if e.returncode == 124:
                    logger.error(lambda: "Timeout while running set_wallpaper script, killed")
                logger.exception(
                    lambda: "Exception when calling set_wallpaper script: %d" % e.returncode
                )
        else:
            logger.error(lambda: "set_wallpaper script is missing or not executable: " + script)
            if self.gsettings:
                self.gsettings.set_string("picture-uri", "file://" + wallpaper)
                self.gsettings.apply()

    def show_hide_history(self, widget=None):
        if self.thumbs_manager.is_showing("history"):
            self.thumbs_manager.hide(force=True)
        else:
            self.thumbs_manager.show(self.used, type="history")
            self.thumbs_manager.pin()
        self.update_indicator(auto_changed=False)

    def show_hide_downloads(self, widget=None):
        if self.thumbs_manager.is_showing("downloads"):
            self.thumbs_manager.hide(force=True)
        else:
            downloaded = list(
                Util.list_files(
                    files=[],
                    folders=[self.real_download_folder],
                    filter_func=Util.is_image,
                    randomize=False,
                )
            )
            downloaded = sorted(downloaded, key=lambda f: os.stat(f).st_mtime, reverse=True)
            self.thumbs_manager.show(downloaded, type="downloads")
            self.thumbs_manager.pin()
        self.update_indicator(auto_changed=False)

    def show_hide_wallpaper_selector(self, widget=None):
        pref_dialog = self.get_preferences_dialog()
        if self.thumbs_manager.is_showing("selector"):
            self.thumbs_manager.hide(force=True)
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
                        logger.warning(
                            lambda: "Persisted last_change_time after current time, setting to current time"
                        )
                        self.last_change_time = now
                logger.info(
                    lambda: "Change interval >= 6 hours, using persisted last_change_time "
                    + str(self.last_change_time)
                )
                logger.info(
                    lambda: "Still to wait: %d seconds"
                    % max(0, self.options.change_interval - (time.time() - self.last_change_time))
                )
            except Exception:
                logger.info(lambda: "Could not read last change time, setting it to current time")
                self.last_change_time = now
        else:
            logger.info(
                lambda: "Change interval < 6 hours, ignore persisted last_change_time, "
                "wait initially the whole interval: " + str(self.options.change_interval)
            )

    def save_history(self):
        try:
            start = max(0, self.position - 100)  # TODO do we want to remember forward history?
            end = min(self.position + 100, len(self.used))
            to_save = self.used[start:end]
            with open(os.path.join(self.config_folder, "history.txt"), "w", encoding="utf8") as f:
                f.write("%d\n" % (self.position - start))
                for file in to_save:
                    f.write(file + "\n")
        except Exception:
            logger.exception(lambda: "Could not save history")

    def load_history(self):
        self.used = []
        self.position = 0
        self.no_effects_on = None

        try:
            with open(os.path.join(self.config_folder, "history.txt"), "r", encoding="utf8") as f:
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
            if os.path.normpath(os.path.dirname(current)) == os.path.normpath(
                self.wallpaper_folder
            ) or os.path.basename(current).startswith("variety-copied-wallpaper-"):

                try:
                    with open(
                        os.path.join(self.wallpaper_folder, "wallpaper.jpg.txt"), encoding="utf8"
                    ) as f:
                        current = f.read().strip()
                except Exception:
                    logger.exception(lambda: "Cannot read wallpaper.jpg.txt")

        self.current = current
        if self.current and (
            self.position >= len(self.used) or current != self.used[self.position]
        ):
            self.used.insert(0, self.current)
            self.position = 0

    def disable_quotes(self, widget=None):
        self.options.quotes_enabled = False
        self.quote = None

        if self.preferences_dialog:
            self.preferences_dialog.ui.quotes_enabled.set_active(False)

        self.options.write()
        self.update_indicator(auto_changed=False)
        if self.quotes_engine:
            self.quotes_engine.stop()

    def prev_quote(self, widget=None):
        if self.quotes_engine and self.options.quotes_enabled:
            self.quote = self.quotes_engine.prev_quote()
            self.update_indicator()
            self.refresh_texts()

    def next_quote(self, widget=None, bypass_history=False):
        if self.quotes_engine and self.options.quotes_enabled:
            self.quote = self.quotes_engine.next_quote(bypass_history)
            self.update_indicator()
            self.refresh_texts()

    def quote_copy_to_clipboard(self, widget=None):
        if self.quote:
            text = self.quote["quote"] + " - " + self.quote["author"]
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(text, -1)
            clipboard.store()

    def reload_quote_favorites_contents(self):
        self.quote_favorites_contents = ""
        try:
            if os.path.isfile(self.options.quotes_favorites_file):
                with open(self.options.quotes_favorites_file, encoding="utf8") as f:
                    self.quote_favorites_contents = f.read()
        except Exception:
            logger.exception(
                lambda: "Could not load favorite quotes file %s"
                % self.options.quotes_favorites_file
            )
            self.quote_favorites_contents = ""

    def current_quote_to_text(self):
        return (
            self.quote["quote"]
            + ("\n-- " + self.quote["author"] if self.quote["author"] else "")
            + "\n%\n"
            if self.quote
            else ""
        )

    def quote_save_to_favorites(self, widget=None):
        if self.quote:
            try:
                self.reload_quote_favorites_contents()
                if self.quote_favorites_contents.find(self.current_quote_to_text()) == -1:
                    with open(self.options.quotes_favorites_file, "a") as f:
                        text = self.current_quote_to_text()
                        f.write(text)
                    self.reload_quote_favorites_contents()
                    self.update_indicator()
                    self.show_notification(
                        "Saved", "Saved to %s" % self.options.quotes_favorites_file
                    )
                else:
                    self.show_notification(_("Already in Favorites"))
            except Exception:
                logger.exception(lambda: "Could not save quote to favorites")
                self.show_notification(
                    "Oops, something went wrong when trying to save the quote to the favorites file"
                )

    def quote_view_favorites(self, widget=None):
        if os.path.isfile(self.options.quotes_favorites_file):
            subprocess.Popen(["xdg-open", self.options.quotes_favorites_file])

    def on_quotes_pause_resume(self, widget=None, change_enabled=None):
        if change_enabled is None:
            self.options.quotes_change_enabled = not self.options.quotes_change_enabled
        else:
            self.options.quotes_change_enabled = change_enabled

        if self.preferences_dialog:
            self.preferences_dialog.ui.quotes_change_enabled.set_active(
                self.options.quotes_change_enabled
            )

        self.options.write()
        self.update_indicator(auto_changed=False)
        if self.quotes_engine:
            self.quotes_engine.on_options_updated(False)

    def view_quote(self, widget=None):
        if self.quote and self.quote.get("link", None):
            webbrowser.open_new_tab(self.quote["link"])

    def google_quote_text(self, widget=None):
        if self.quote and self.quote["quote"]:
            url = "https://google.com/search?q=" + urllib.parse.quote_plus(
                self.quote["quote"].encode("utf8")
            )
            webbrowser.open_new_tab(url)

    def google_quote_author(self, widget=None):
        if self.quote and self.quote["author"]:
            url = "https://google.com/search?q=" + urllib.parse.quote_plus(
                self.quote["author"].encode("utf8")
            )
            webbrowser.open_new_tab(url)

    def google_image_search(self, widget=None):
        if self.image_url:
            url = (
                "https://www.google.com/searchbyimage?safe=off&image_url="
                + urllib.parse.quote_plus(self.image_url.encode("utf8"))
            )
            webbrowser.open_new_tab(url)

    def toggle_no_effects(self, no_effects):
        self.no_effects_on = self.current if no_effects else None
        self.refresh_wallpaper()

    def create_desktop_entry(self):
        """
        Creates a profile-specific desktop entry in ~/.local/share/applications
        This ensures Variety's icon context menu is for the correct profile, and also that
        application's windows will be correctly grouped by profile.
        """
        if is_default_profile():
            return

        try:
            desktop_file_folder = os.path.expanduser("~/.local/share/applications")
            profile_name = get_profile_short_name()
            desktop_file_path = os.path.join(desktop_file_folder, get_desktop_file_name())

            should_notify = not os.path.exists(desktop_file_path)

            Util.makedirs(desktop_file_folder)
            Util.copy_with_replace(
                varietyconfig.get_data_file("variety-profile.desktop.template"),
                desktop_file_path,
                {
                    "{PROFILE_PATH}": get_profile_path(expanded=True),
                    "{PROFILE_NAME}": (profile_name),
                    "{VARIETY_PATH}": Util.get_exec_path(),
                    "{WM_CLASS}": get_profile_wm_class(),
                },
            )

            if should_notify:
                self.show_notification(
                    _("Variety: New desktop entry"),
                    _(
                        "We created a new desktop entry in ~/.local/share/applications "
                        'to run Variety with profile "{}". Find it in the application launcher.'
                    ).format(profile_name),
                )
        except Exception:
            logger.exception(lambda: "Could not create desktop entry for a run with --profile")

    def create_autostart_entry(self):
        try:
            autostart_file_path = get_autostart_file_path()
            Util.makedirs(os.path.dirname(autostart_file_path))
            should_notify = not os.path.exists(autostart_file_path)

            Util.copy_with_replace(
                varietyconfig.get_data_file("variety-autostart.desktop.template"),
                autostart_file_path,
                {
                    "{PROFILE_PATH}": get_profile_path(expanded=True),
                    "{VARIETY_PATH}": Util.get_exec_path(),
                    "{WM_CLASS}": get_profile_wm_class(),
                },
            )

            if should_notify:
                self.show_notification(
                    _("Variety: Created autostart desktop entry"),
                    _(
                        "We created a new desktop entry in ~/.config/autostart. "
                        "Variety should start automatically on next restart."
                    ),
                )
        except Exception:
            logger.exception(lambda: "Error while creating autostart desktop entry")
            self.show_notification(
                _("Could not create autostart entry"),
                _(
                    "An error occurred while creating the autostart desktop entry\n"
                    "Please run from a terminal with the -v flag and try again."
                ),
            )

    def on_start_slideshow(self, widget=None):
        def _go():
            try:
                if self.options.slideshow_mode.lower() != "window":
                    subprocess.call(["killall", "-9", "variety-slideshow"])

                args = ["variety-slideshow"]
                args += ["--seconds", str(self.options.slideshow_seconds)]
                args += ["--fade", str(self.options.slideshow_fade)]
                args += ["--zoom", str(self.options.slideshow_zoom)]
                args += ["--pan", str(self.options.slideshow_pan)]
                if "," in self.options.slideshow_sort_order.lower():
                    sort = self.options.slideshow_sort_order.lower().split(",")[0]
                    order = self.options.slideshow_sort_order.lower().split(",")[1]
                else:
                    sort = self.options.slideshow_sort_order.lower()
                    order = "asc"
                args += ["--sort", sort]
                args += ["--order", order]
                args += ["--mode", self.options.slideshow_mode.lower()]

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
                if self.options.slideshow_custom_enabled and os.path.isdir(
                    self.options.slideshow_custom_folder
                ):
                    folders.append(self.options.slideshow_custom_folder)

                if not images and not folders:
                    folders.append(self.options.favorites_folder)

                if not list(
                    Util.list_files(
                        files=images,
                        folders=folders,
                        filter_func=Util.is_image,
                        max_files=1,
                        randomize=False,
                    )
                ):
                    self.show_notification(
                        _("No images"), _("There are no images in the slideshow folders")
                    )
                    return

                args += images
                args += folders

                if self.options.slideshow_monitor.lower() != "all":
                    try:
                        args += ["--monitor", str(int(self.options.slideshow_monitor))]
                    except:
                        pass
                    subprocess.Popen(args)
                else:
                    screen = Gdk.Screen.get_default()
                    for i in range(0, screen.get_n_monitors()):
                        new_args = list(args)
                        new_args += ["--monitor", str(i + 1)]
                        subprocess.Popen(new_args)
            except:
                logger.exception("Could not start slideshow:")

        threading.Thread(target=_go).start()
