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

"""Code to add AppIndicator."""

from gi.repository import Gtk # pylint: disable=E0611
import os
import threading

from variety.Smart import Smart
from variety.Util import Util

THEME_ICON_NAME = "variety-indicator"
THEME_ICON_NAME_DARK = "variety-indicator-dark"

try:
    from gi.repository import AppIndicator3 # pylint: disable=E0611
    use_appindicator = True
except ImportError:
    use_appindicator = False

from variety_lib import varietyconfig

from variety import _, _u

import logging
logger = logging.getLogger('variety')

class Indicator:
    def __init__(self, window):
        self.parent = window
        self.create_menu(window)
        self.create_indicator(window)

    def create_menu(self, window):
        self.menu = Gtk.Menu()

        if not Util.is_unity():
            self.next_main = Gtk.MenuItem(_("_Next"))
            self.next_main.set_use_underline(True)
            self.next_main.connect("activate", window.next_wallpaper)
            self.menu.append(self.next_main)

            self.prev_main = Gtk.MenuItem(_("_Previous"))
            self.prev_main.set_use_underline(True)
            self.prev_main.connect("activate", window.prev_wallpaper)
            self.menu.append(self.prev_main)

            self.menu.append(Gtk.SeparatorMenuItem.new())

        self.file_label = Gtk.MenuItem(_("Current desktop wallpaper"))
        self.file_label.connect("activate", window.open_file)
        self.menu.append(self.file_label)

        self.show_origin = Gtk.MenuItem(_("Show origin"))
        self.show_origin.connect("activate", window.on_show_origin)
        self.show_origin.set_sensitive(False)
        self.menu.append(self.show_origin)

        self.show_author = Gtk.MenuItem("Show author")
        self.show_author.connect("activate", window.on_show_author)
        self.show_author.set_sensitive(False)
        self.show_author.set_visible(False)
        self.menu.append(self.show_author)

        self.copy_to_favorites = Gtk.MenuItem(_("Copy to _Favorites"))
        self.copy_to_favorites.set_use_underline(True)
        self.copy_to_favorites.connect("activate", window.copy_to_favorites)
        self.menu.append(self.copy_to_favorites)

        self.move_to_favorites = Gtk.MenuItem(_("Move to Favorites"))
        self.move_to_favorites.set_use_underline(True)
        self.move_to_favorites.connect("activate", window.move_to_favorites)
        self.move_to_favorites.set_visible(False)
        self.menu.append(self.move_to_favorites)

        self.trash = Gtk.MenuItem(_("Delete to _Trash"))
        self.trash.set_use_underline(True)
        self.trash.connect("activate", window.move_to_trash)
        self.menu.append(self.trash)

        self.menu.append(Gtk.SeparatorMenuItem.new())

        self.image_menu = Gtk.Menu()

        self.next = Gtk.MenuItem(_("_Next"))
        self.next.set_use_underline(True)
        self.next.connect("activate", window.next_wallpaper)
        self.image_menu.append(self.next)

        self.prev = Gtk.MenuItem(_("_Previous"))
        self.prev.set_use_underline(True)
        self.prev.connect("activate", window.prev_wallpaper)
        self.image_menu.append(self.prev)

        self.fast_forward = Gtk.MenuItem(_("_Next, skipping forward history"))
        self.fast_forward.set_use_underline(True)
        def _fast_forward(widget):
            window.next_wallpaper(widget, bypass_history=True)
        self.fast_forward.connect("activate", _fast_forward)
        self.image_menu.append(self.fast_forward)

        self.image_menu.append(Gtk.SeparatorMenuItem.new())
        self.scroll_tip = Gtk.MenuItem(_("Tip: Scroll wheel over icon\nfor Next and Previous"))
        self.scroll_tip.set_sensitive(False)
        self.image_menu.append(self.scroll_tip)

        self.image_menu.append(Gtk.SeparatorMenuItem.new())

        self.pause_resume = Gtk.MenuItem(_("Pause on current"))
        self.pause_resume.connect("activate", window.on_pause_resume)
        self.image_menu.append(self.pause_resume)

        self.image_item = Gtk.MenuItem(_("_Image"))
        self.image_item.set_use_underline(True)
        self.image_item.set_submenu(self.image_menu)
        self.menu.append(self.image_item)

        self.image_menu.append(Gtk.SeparatorMenuItem.new())

        self.focus = Gtk.MenuItem(_("Where is it from?"))
        self.focus.connect("activate", window.focus_in_preferences)
        self.image_menu.append(self.focus)

        self.no_effects = Gtk.CheckMenuItem(_("Show without effects"))
        self.no_effects.set_active(False)
        self.no_effects.set_use_underline(True)
        def _toggle_no_effects(widget=None):
            window.toggle_no_effects(self.no_effects.get_active())
        self.no_effects_handler_id = self.no_effects.connect("toggled", _toggle_no_effects)
        self.image_menu.append(self.no_effects)

        self.google_image = Gtk.MenuItem(_("Google Image Search"))
        self.google_image.connect("activate", window.google_image_search)
        self.image_menu.append(self.google_image)

        self.image_menu.append(Gtk.SeparatorMenuItem.new())

        self.publish_fb = Gtk.MenuItem(_("Share on Facebook"))
        self.publish_fb.connect("activate", window.publish_on_facebook)
        self.image_menu.append(self.publish_fb)

        self.rating_separator = Gtk.SeparatorMenuItem.new()
        self.image_menu.append(self.rating_separator)

        self.rating = Gtk.MenuItem(_("Set EXIF Rating"))
        self.image_menu.append(self.rating)

        # self.image_item = Gtk.MenuItem(_("_Image"))
        # self.image_item.set_use_underline(True)
        # self.image_item.set_submenu(self.image_menu)
        # self.menu.append(self.image_item)
        #
        self.sfw_menu = Gtk.Menu()
        self.sfw_menu.set_sensitive(False)
        threading.Timer(2, self.populate_sfw_menu).start()

        self.sfw_menu_item = Gtk.MenuItem(_("Report NSFW image"))
        self.sfw_menu_item.set_sensitive(False)
        self.sfw_menu_item.set_use_underline(True)
        self.sfw_menu_item.set_submenu(self.sfw_menu)
        self.menu.append(self.sfw_menu_item)

        self.quotes_menu = Gtk.Menu()

        self.next_quote = Gtk.MenuItem(_("_Next"))
        self.next_quote.set_use_underline(True)
        self.next_quote.connect("activate", window.next_quote)
        self.quotes_menu.append(self.next_quote)

        self.prev_quote = Gtk.MenuItem(_("_Previous"))
        self.prev_quote.set_use_underline(True)
        self.prev_quote.connect("activate", window.prev_quote)
        self.quotes_menu.append(self.prev_quote)

        self.fast_forward_quote = Gtk.MenuItem(_("_Next, skipping forward history"))
        self.fast_forward_quote.set_use_underline(True)
        def _fast_forward_quote(widget):
            window.next_quote(widget, bypass_history=True)
        self.fast_forward_quote.connect("activate", _fast_forward_quote)
        self.quotes_menu.append(self.fast_forward_quote)

        self.quotes_menu.append(Gtk.SeparatorMenuItem.new())

        self.quotes_pause_resume = Gtk.MenuItem(_("Pause on current"))
        self.quotes_pause_resume.connect("activate", window.on_quotes_pause_resume)
        self.quotes_menu.append(self.quotes_pause_resume)

        self.quotes_menu.append(Gtk.SeparatorMenuItem.new())

        self.quote_favorite = Gtk.MenuItem(_("Save to Favorites"))
        self.quote_favorite.set_use_underline(True)
        self.quote_favorite.connect("activate", window.quote_save_to_favorites)
        self.quotes_menu.append(self.quote_favorite)

        self.quote_view_favs = Gtk.MenuItem(_("View Favorites..."))
        self.quote_view_favs.set_use_underline(True)
        self.quote_view_favs.connect("activate", window.quote_view_favorites)
        self.quotes_menu.append(self.quote_view_favs)

        self.quotes_menu.append(Gtk.SeparatorMenuItem.new())

        self.quote_clipboard = Gtk.MenuItem(_("Copy to Clipboard"))
        self.quote_clipboard.set_use_underline(True)
        self.quote_clipboard.connect("activate", window.quote_copy_to_clipboard)
        self.quotes_menu.append(self.quote_clipboard)

        self.view_quote = Gtk.MenuItem()
        self.view_quote.set_use_underline(True)
        self.view_quote.connect("activate", window.view_quote)
        self.quotes_menu.append(self.view_quote)

        self.google_quote_text = Gtk.MenuItem(_("Google Quote"))
        self.google_quote_text.set_use_underline(True)
        self.google_quote_text.connect("activate", window.google_quote_text)
        self.quotes_menu.append(self.google_quote_text)

        self.google_quote_author = Gtk.MenuItem(_("Google Author"))
        self.google_quote_author.set_use_underline(True)
        self.google_quote_author.connect("activate", window.google_quote_author)
        self.quotes_menu.append(self.google_quote_author)

        self.quote_fb = Gtk.MenuItem(_("Share on Facebook"))
        self.quote_fb.set_use_underline(True)
        self.quote_fb.connect("activate", window.publish_quote_on_facebook)
        self.quotes_menu.append(self.quote_fb)

        self.quotes_menu.append(Gtk.SeparatorMenuItem.new())

        self.quotes_preferences = Gtk.MenuItem(_("Preferences..."))
        self.quotes_preferences.set_use_underline(True)
        def _quotes_prefs(widget=None):
            window.preferences_dialog.ui.notebook.set_current_page(1)
            window.on_mnu_preferences_activate()
        self.quotes_preferences.connect("activate", _quotes_prefs)
        self.quotes_menu.append(self.quotes_preferences)

        self.quotes_disable = Gtk.MenuItem(_("Turn off"))
        self.quotes_disable.set_use_underline(True)
        self.quotes_disable.connect("activate", window.disable_quotes)
        self.quotes_menu.append(self.quotes_disable)


        self.quotes = Gtk.MenuItem(_("_Quote"))
        self.quotes.set_use_underline(True)
        self.quotes.set_submenu(self.quotes_menu)
        self.menu.append(self.quotes)

        self.menu.append(Gtk.SeparatorMenuItem.new())

        self.history = Gtk.CheckMenuItem(_("_History"))
        self.history.set_active(False)
        self.history.set_use_underline(True)
        self.history_handler_id = self.history.connect("toggled", window.show_hide_history)
        self.menu.append(self.history)

        self.selector = Gtk.CheckMenuItem(_("_Wallpaper Selector"))
        self.selector.set_active(False)
        self.selector.set_use_underline(True)
        self.selector_handler_id = self.selector.connect("toggled", window.show_hide_wallpaper_selector)
        self.menu.append(self.selector)

        self.downloads = Gtk.CheckMenuItem(_("Recent _Downloads"))
        self.downloads.set_active(False)
        self.downloads.set_use_underline(True)
        self.downloads_handler_id = self.downloads.connect("toggled", window.show_hide_downloads)
        self.menu.append(self.downloads)

        try:
            from varietyslideshow import varietyslideshow
        except:
            logger.warning('Variety Slideshow is not installed. '
                           'Install it with "sudo apt-get install variety-slideshow", '
                           'read more here: http://peterlevi.com/variety/slideshow/')
        else:
            self.menu.append(Gtk.SeparatorMenuItem.new())

            self.slideshow = Gtk.MenuItem(_("Start Slideshow"))
            self.slideshow.connect("activate", window.on_start_slideshow)
            self.menu.append(self.slideshow)

        self.menu.append(Gtk.SeparatorMenuItem.new())

        self.preferences = Gtk.MenuItem(_("Preferences..."))
        self.preferences.connect("activate", window.on_mnu_preferences_activate)
        self.menu.append(self.preferences)

        self.about = Gtk.MenuItem(_("About"))
        self.about.connect("activate", window.on_mnu_about_activate)
        self.menu.append(self.about)

        self.donate = Gtk.MenuItem(_("Donate"))
        self.donate.connect("activate", window.on_mnu_donate_activate)
        self.menu.append(self.donate)

        self.quit = Gtk.MenuItem(_("Quit"))
        self.quit.connect("activate",window.on_quit)
        self.menu.append(self.quit)

        self.menu.show_all()

    def create_indicator(self, window):
        self.indicator = None
        self.status_icon = None
        self.visible = True

        def pos(menu, icon):
            return Gtk.StatusIcon.position_menu(self.menu, icon)

        def right_click_event(icon, button, time):
            self.menu.popup(None, None, pos, self.status_icon, 0, time)

        def left_click_event(data):
            self.menu.popup(None, None, pos, self.status_icon, 0, Gtk.get_current_event_time())

        def on_indicator_scroll_status_icon(status_icon, event):
            window.on_indicator_scroll(None, 1, event.direction)

        icon_path = varietyconfig.get_data_file("media", "variety-indicator.png")
        if use_appindicator:
            self.indicator = AppIndicator3.Indicator.new('variety', '', AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            self.indicator.set_icon(icon_path)
            self.indicator.connect("scroll-event", window.on_indicator_scroll)
            self.indicator.set_menu(self.menu)
        else:
            self.status_icon = Gtk.StatusIcon.new_from_file(icon_path)
            self.status_icon.set_visible(True)
            self.status_icon.connect("activate", left_click_event)
            self.status_icon.connect("popup-menu", right_click_event)
            self.status_icon.connect("scroll-event", on_indicator_scroll_status_icon)

    def set_visible(self, visible):
        self.visible = visible
        if visible:
            if self.indicator:
                logger.info(lambda: "Showing indicator icon")
                self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            if self.status_icon:
                logger.info(lambda: "Showing status icon")
                self.status_icon.set_visible(True)
        else:
            if self.indicator:
                logger.info(lambda: "Hiding indicator icon")
                self.indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
            if self.status_icon:
                logger.info(lambda: "Hiding status icon")
                self.status_icon.set_visible(False)

    def set_icon(self, icon):
        def set_from_theme_icon(name):
            if self.indicator:
                logger.info(lambda: "Showing indicator icon %s from GTK theme" % name)
                self.indicator.set_icon(name)
            if self.status_icon:
                logger.info(lambda: "Showing status icon %s from GTK theme" % name)
                self.status_icon.set_from_icon_name(name)

        if icon == "Light":
            if Gtk.IconTheme.get_default().has_icon(THEME_ICON_NAME):
                set_from_theme_icon(THEME_ICON_NAME)
                return
            else:
                icon_path = varietyconfig.get_data_file("media", "variety-indicator.png")
        elif icon == "Dark":
            if Gtk.IconTheme.get_default().has_icon(THEME_ICON_NAME_DARK):
                set_from_theme_icon(THEME_ICON_NAME_DARK)
                return
            else:
                icon_path = varietyconfig.get_data_file("media", "variety-indicator-dark.png")
        elif icon and os.access(icon, os.R_OK) and Util.is_image(icon):
            icon_path = icon
        else:
            icon_path = varietyconfig.get_data_file("media", "variety-indicator.png")

        if self.indicator:
            logger.info(lambda: "Showing indicator icon image: " + icon_path)
            self.indicator.set_icon(icon_path)
        if self.status_icon:
            logger.info(lambda: "Showing status icon image: " + icon_path)
            self.status_icon.set_from_file(icon_path)

    def get_visible(self):
        return self.visible

    def populate_sfw_menu(self):
        try:
            self.rating_items = []
            sfw_ratings = Smart.get_all_sfw_ratings()

            def _gui_update(sfw_ratings):
                try:
                    def _add_menuitem(rating):
                        menuitem = Gtk.ImageMenuItem(_(rating['label_long']))
                        menuitem.set_visible(True)

                        def _rate(*args, **kwargs):
                            self.parent.report_sfw_rating(file=None, rating=rating['rating'])

                        menuitem.connect("activate", _rate)
                        try:
                            menuitem.set_always_show_image(True)
                            image = Gtk.Image()
                            image.set_from_file(varietyconfig.get_data_file("media", "sfw-%s.svg" % rating['rating']))
                            menuitem.set_image(image)
                        except:
                            logger.exception(lambda: "Could not set image to NSFW menuitem:")
                        self.sfw_menu.append(menuitem)
                        self.rating_items.append(menuitem)

                    map(_add_menuitem, reversed(sfw_ratings))

                    separator = Gtk.SeparatorMenuItem.new()
                    separator.set_visible(True)
                    self.sfw_menu.append(separator)

                    self.safe_mode = Gtk.CheckMenuItem(_("_Safe mode"))
                    self.safe_mode.set_visible(True)
                    self.safe_mode.set_active(self.parent.options.safe_mode)
                    self.safe_mode.set_use_underline(True)
                    self.safe_mode_handler_id = self.safe_mode.connect("toggled", self.parent.on_safe_mode_toggled)
                    self.sfw_menu.append(self.safe_mode)

                    self.sfw_menu_item.set_sensitive(True)

                    self.parent.update_indicator()
                except Exception:
                    logger.exception(lambda: 'Oops, could not populate NSFW menu:')

            Util.add_mainloop_task(_gui_update, sfw_ratings)
        except Exception:
            logger.exception(lambda: 'Oops, could not populate NSFW menu:')


def new_application_indicator(window):
    ind = Indicator(window)
    return ind, ind.indicator, ind.status_icon
