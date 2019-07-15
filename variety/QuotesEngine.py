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

import logging
import random
import threading
import time

from variety.plugins.IQuoteSource import IQuoteSource
from variety.Util import _

logger = logging.getLogger("variety")


class QuotesEngine:
    def __init__(self, parent=None):
        self.parent = parent
        self.quote = None
        self.started = False
        self.running = False
        self.used = []

    def update_plugins(self):
        for p in self.parent.jumble.get_plugins(IQuoteSource):
            name = p["info"]["name"]
            if name in self.parent.options.quotes_disabled_sources:
                try:
                    p["plugin"].deactivate()
                except Exception:
                    logger.exception(lambda: "Error deactivating %s" % name)
            else:
                try:
                    p["plugin"].activate()
                except Exception:
                    logger.exception(lambda: "Error activating %s" % name)

        self.plugins = self.parent.jumble.get_plugins(IQuoteSource, active=True)

    def stop(self):
        self.running = False
        self.started = False
        self.update_plugins()

    def start(self):
        if self.started or not self.parent.options.quotes_enabled:
            return

        logger.info(lambda: "Starting QuotesEngine")

        self.update_plugins()

        self.prepared = []
        self.position = 0
        self.prepared_lock = threading.Lock()
        self.prepare_event = threading.Event()
        self.change_event = threading.Event()

        self.cache = {}

        self.started = True
        self.running = True

        self.last_change_time = time.time()
        self.last_error_notification_time = 0

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

        self.used = self.used[self.position :]
        self.position = 0
        if self.quote:
            self.used.insert(0, self.quote)
        if len(self.used) > 200:
            self.used = self.used[:200]

        return self.quote

    def on_options_updated(self, clear_prepared=True):
        if clear_prepared:
            logger.info(lambda: "Quotes: clearing prepared and updating plugins")
            with self.prepared_lock:
                self.prepared = []
            self.update_plugins()
        self.prepare_event.set()
        self.change_event.set()

    def regular_change_thread(self):
        logger.info(lambda: "Quotes regular change thread running")

        while self.running:
            try:
                while (
                    not self.parent.options.quotes_change_enabled
                    or (time.time() - self.last_change_time)
                    < self.parent.options.quotes_change_interval
                ):
                    if not self.running:
                        return
                    now = time.time()
                    wait_more = self.parent.options.quotes_change_interval - max(
                        0, (now - self.last_change_time)
                    )
                    if self.parent.options.quotes_change_enabled:
                        self.change_event.wait(max(0, wait_more))
                    else:
                        self.change_event.wait()
                    self.change_event.clear()
                if not self.running:
                    return
                if not self.parent.options.quotes_change_enabled:
                    continue
                logger.info(lambda: "Quotes regular_change changes quote")
                self.last_change_time = time.time()
                self.parent.quote = self.change_quote()
                self.parent.refresh_texts()
            except Exception:
                logger.exception(lambda: "Exception in regular_change_thread")

    def prepare_thread(self):
        logger.info(lambda: "Quotes prepare thread running")

        while self.running:
            try:
                while (
                    self.running and self.parent.options.quotes_enabled and len(self.prepared) < 10
                ):
                    logger.info(
                        lambda: "Quotes prepared buffer contains %s quotes, fetching a quote"
                        % len(self.prepared)
                    )
                    quote = self.get_one_quote()
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
                logger.exception(lambda: "Error in quotes prepare thread:")

            self.prepare_event.wait()
            self.prepare_event.clear()

    def get_one_quote(self):
        keywords = []
        if self.parent.options.quotes_tags.strip():
            keywords = self.parent.options.quotes_tags.split(",")
        authors = []
        if self.parent.options.quotes_authors.strip():
            authors = self.parent.options.quotes_authors.split(",")

        category, search = ("random", "")
        if keywords or authors:
            category, search = random.choice(
                [("keyword", k) for k in keywords] + [("author", a) for a in authors]
            )

        plugins = list(self.plugins)
        if not plugins:
            self.parent.show_notification(
                _("No quote plugins"), _("There are no quote plugins installed")
            )
            raise Exception("No quote plugins")
        if keywords or authors:
            plugins = [p for p in self.plugins if p["plugin"].supports_search()]
            if not plugins:
                self.parent.show_notification(
                    _("No suitable quote plugins"),
                    _("You have no quote plugins which support searching by keywords and authors"),
                )
                raise Exception("No quote plugins")

        error_plugins = []
        count_plugins = len(plugins)
        while self.running and self.parent.options.quotes_enabled:
            if not plugins:
                if (
                    time.time() - self.last_error_notification_time > 3600
                    and len(self.prepared) + len(self.used) < 5
                ):
                    self.last_error_notification_time = time.time()
                    if len(error_plugins) == count_plugins:
                        self.parent.show_notification(
                            _("Could not fetch quotes"),
                            _("Quotes services may be down, we will continue trying"),
                        )
                    else:
                        self.parent.show_notification(
                            _("Could not find quotes"),
                            _("Maybe you are searching for something very obscure?"),
                        )
                return None

            plugin = random.choice(plugins)
            plugin_name = plugin["info"]["name"]
            self.cache.setdefault(plugin_name, {"random": {}, "keyword": {}, "author": {}})
            self.cache[plugin_name][category].setdefault(search, {})
            cached = self.cache[plugin_name][category][search]

            if not cached:
                try:
                    if category == "random":
                        quotes = plugin["plugin"].get_random()
                    elif category == "keyword":
                        quotes = plugin["plugin"].get_for_keyword(search)
                    elif category == "author":
                        quotes = plugin["plugin"].get_for_author(search)
                    else:
                        raise RuntimeError("Unknown category")

                    if quotes:
                        for q in quotes:
                            if len(q["quote"]) < self.parent.options.quotes_max_length:
                                cached[q["quote"]] = q

                except Exception:
                    logger.exception(lambda: "Exception in quote plugin")
                    plugins.remove(plugin)
                    error_plugins.append(plugin)
                    continue

            if not cached:
                logger.warning(lambda: "No quotes for '%s' for plugin %s" % (search, plugin_name))
                plugins.remove(plugin)
                continue

            quote = random.choice(list(cached.values()))
            del cached[quote["quote"]]
            if not cached:
                del cached

            return quote
