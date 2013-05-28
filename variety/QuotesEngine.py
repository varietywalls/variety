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

import random
import time
from variety.plugins.IQuoteSource import IQuoteSource

import logging
import threading

logger = logging.getLogger('variety')

import gettext
from gettext import gettext as _
gettext.textdomain('variety')

class QuotesEngine:
    def __init__(self, parent = None):
        self.parent = parent
        self.quote = None
        self.prepared = []
        self.used = []
        self.position = 0
        self.prepared_lock = threading.Lock()
        self.prepare_event = threading.Event()
        self.change_event = threading.Event()
        self.started = False
        self.running = False
        self.last_change_time = time.time()
        self.last_error_notification_time = 0

    def start(self):
        if self.started:
            return

        if self.parent.options.quotes_enabled:
            logger.info("Starting QuotesEngine")
            self.started = False
            self.running = True

            prep_thread = threading.Thread(target=self.prepare_thread)
            prep_thread.daemon = True
            prep_thread.start()

            change_thread = threading.Thread(target=self.regular_change_thread)
            change_thread.daemon = True
            change_thread.start()

    def quit(self):
        self.running = False
        self.prepare_event.set()

    def get_quote(self):
        return self.quote

    def has_previous(self):
        return self.position < len(self.used) - 1

    def prev_quote(self):
        self.last_change_time = time.time()
        self.position += 1
        if self.position >= len(self.used):
            if self.used:
                self.quote = self.choose_some_quote()
            self.used.append(self.quote)
        else:
            self.quote = self.used[self.position]
        return self.quote

    def bypass_history(self):
        self.position = 0

    def next_quote(self, bypass_history=False):
        self.last_change_time = time.time()
        if self.position > 0 and not bypass_history:
            self.position -= 1
            if self.position < len(self.used) - 1:
                self.quote = self.used[self.position]
            return self.quote
        else:
            if bypass_history:
                self.bypass_history()
            return self.change_quote()

    def choose_some_quote(self):
        with self.prepared_lock:
            if [x for x in self.prepared if x != self.quote]:
                self.quote = random.choice([x for x in self.prepared if x != self.quote])
            elif [x for x in self.used if x != self.quote]:
                self.quote = random.choice([x for x in self.used if x != self.quote])
            elif self.prepared:
                self.quote = random.choice(self.prepared)
            elif self.used:
                self.quote = random.choice(self.used)

            if self.quote in self.prepared:
                self.prepared.remove(self.quote)
                self.prepare_event.set()

            return self.quote

    def change_quote(self):
        self.last_change_time = time.time()

        self.choose_some_quote()

        self.used = self.used[self.position:]
        self.position = 0
        if self.quote:
            self.used.insert(0, self.quote)
        if len(self.used) > 200:
            self.used = self.used[:200]

        return self.quote

    def on_options_updated(self, clear_prepared = True):
        if clear_prepared:
            with self.prepared_lock:
                self.prepared = []
        self.prepare_event.set()
        self.change_event.set()

    def regular_change_thread(self):
        logger.info("Quotes regular change thread running")

        while self.running:
            try:
                while not self.parent.options.quotes_change_enabled or \
                      (time.time() - self.last_change_time) < self.parent.options.quotes_change_interval:
                    if not self.running:
                        return
                    now = time.time()
                    wait_more = self.parent.options.quotes_change_interval - max(0, (now - self.last_change_time))
                    if self.parent.options.quotes_change_enabled:
                        self.change_event.wait(max(0, wait_more))
                    else:
                        self.change_event.wait()
                    self.change_event.clear()
                if not self.running:
                    return
                if not self.parent.options.quotes_change_enabled:
                    continue
                logger.info("Quotes regular_change changes quote")
                self.last_change_time = time.time()
                self.parent.quote = self.change_quote()
                self.parent.refresh_texts()
            except Exception:
                logger.exception("Exception in regular_change_thread")

    def prepare_thread(self):
        logger.info("Quotes prepare thread running")

        while self.running:
            try:
                while self.running and self.parent.options.quotes_enabled and len(self.prepared) < 10:
                    logger.info("Quotes prepared buffer contains %s quotes, fetching a quote" % len(self.prepared))
                    quote = self.download_one_quote()
                    if quote:
                        with self.prepared_lock:
                            self.prepared.append(quote)
                        if self.parent.options.quotes_enabled and self.parent.quote is None:
                            self.parent.quote = self.change_quote()
                            self.parent.refresh_texts()

                    time.sleep(2)

                if not self.running:
                    return

            except Exception:
                logger.exception("Error in quotes prepare thread:")

            self.prepare_event.wait()
            self.prepare_event.clear()


    def download_one_quote(self):
        keywords = None
        if self.parent.options.quotes_tags.strip():
            keywords = self.parent.options.quotes_tags.split(",")

        plugins = self.parent.jumble.get_plugins(IQuoteSource)
        plugins = [p for p in plugins if (not keywords or p["plugin"].supports_keywords())]
        if not plugins:
            self.parent.show_notification(_("No suitable quote plugins"),
                                          _("You have no quote plugins which support searching by keyword"))
            raise Exception("No quote plugins")

        skip = []
        while self.running and self.parent.options.quotes_enabled:
            active = [p for p in plugins if p not in skip]

            if not active:
                if time.time() - self.last_error_notification_time > 3600 and len(self.prepared) + len(self.used) < 5:
                    self.last_error_notification_time = time.time()
                    self.parent.show_notification(
                        _("Could not fetch quotes"),
                        _("Quotes services seems to be down, but we will continue trying"))
                return None

            plugin = random.choice(active)
            try:
                quote = plugin["plugin"].get_quote(keywords)
                if not quote:
                    skip.append(plugin)
                elif len(quote["quote"]) < 250:
                    return quote
            except Exception:
                logger.exception("Exception in quote plugin")
                skip.append(plugin)

            time.sleep(2)

        return None
