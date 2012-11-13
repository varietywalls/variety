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

from bs4 import BeautifulSoup
import random
import urllib
import time
from variety.Util import Util

import logging
import threading

logger = logging.getLogger('variety')

class QuotesEngine:
    def __init__(self, parent = None):
        self.parent = parent
        self.prepared = []
        self.used = []
        self.prepared_lock = threading.Lock()
        self.prepare_event = threading.Event()
        self.started = False
        self.running = False

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

    def quit(self):
        self.running = False
        self.prepare_event.set()

    def get_quote(self):
        with self.prepared_lock:
            if self.prepared:
                quote = self.prepared[0]
                self.prepared = self.prepared[1:]
                self.used.insert(0, quote)
                if len(self.used) > 200:
                    self.used = self.used[:200]
                self.prepare_event.set()
                return quote
            elif self.used:
                random.choice(self.used)
            else:
                return None

    def on_options_updated(self):
        with self.prepared_lock:
            self.prepared = []
        self.prepare_event.set()

    def prepare_thread(self):
        logger.info("Quotes prepare thread running")

        while self.running:
            try:
                parent_refreshed = False
                while self.running and self.parent.options.quotes_enabled and len(self.prepared) < 5:
                    logger.info("Quotes prepared buffer contains %s quotes, fetching a quote" % len(self.prepared))
                    quote = self.download_one_quote()
                    if quote:
                        with self.prepared_lock:
                            self.prepared.append(quote)
                        if not parent_refreshed and self.parent.options.quotes_enabled and self.parent.quote is None:
                            self.parent.refresh_texts()
                            parent_refreshed = True

                    time.sleep(2)

                if not self.running:
                    return

            except Exception:
                logger.exception("Error in quotes prepare thread:")

            self.prepare_event.wait()
            self.prepare_event.clear()


    def download_one_quote(self):
        skip = set()
        while self.running and self.parent.options.quotes_enabled:
            url = QuotesEngine.choose_random_feed_url(self.parent.options, skip)
            if not url:
                logger.warning("Could not fetch any quotes")
                return None

            try:
                xml = Util.fetch(url)
                quote = QuotesEngine.extract_quote(xml)
                if not quote:
                    logger.warning("Could not find quotes for URL " + url)
                    skip.add(url)
                elif len(quote["quote"]) < 250:
                    return quote
            except Exception:
                logger.exception("Could not extract quote")
                skip.add(url)

            time.sleep(2)
        return None

    @staticmethod
    def extract_quote(xml):
        bs = BeautifulSoup(xml, "xml")
        item = bs.find("item")
        if not item:
            return None
        link = item.find("link").contents[0].strip()
        s = item.find("description").contents[0]
        author = s[s.rindex('- ') + 1:].strip()
        quote = s[:s.rindex('- ')].strip().replace('"', '').replace('<br>', '\n').replace('<br/>', '\n').strip()
        quote = u"\u201C%s\u201D" % quote
        return {"quote": quote, "author": author, "link": link}

    @staticmethod
    def choose_random_feed_url(options, skip_urls=set()):
        urls = []
        tags = options.quotes_tags.split(",")
        for tag in tags:
            if tag.strip():
                url = "http://www.quotesdaddy.com/feed/tagged/" + urllib.quote_plus(tag.strip())
                if not url in skip_urls:
                    urls.append(url)

        authors = options.quotes_authors.split(",")
        for author in authors:
            if author.strip():
                url = "http://www.quotesdaddy.com/feed/author/" + urllib.quote_plus(author)
                if not url in skip_urls:
                    urls.append(url)

        if not urls:
            urls.append("http://www.quotesdaddy.com/feed")

        return random.choice(urls)
