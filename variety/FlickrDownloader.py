#!/usr/bin/python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2012 Peter Levi <peterlevi@peterlevi.com>
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

import urllib
import urllib2
import random
import os
import json

import logging
from variety import Downloader

logger = logging.getLogger('variety')

random.seed()

API_KEY = "0553a848c09bcfd21d3a984d9408c04e"

class FlickrDownloader(Downloader.Downloader):
    def __init__(self, location, download_folder):
        super(FlickrDownloader, self).__init__("Flickr", location, download_folder)
        self.target_folder = os.path.join(download_folder, "flickr_" + self.convert_to_filename(self.location))
        self.parse_location()
        self.queue = []

    def parse_location(self):
        s = self.location.split(';')
        self.params = {}
        for x in s:
            if len(x) and x.find(':') > 0:
                k, v = x.split(':')
                if k.lower() in ["tags", "user_id", "group_id"]:
                    self.params[k.lower()] = v.replace(' ', '+')

        # slight validation:
        for k in ["tags", "user_id", "group_id"]:
            if k in self.params and len(self.params[k]) > 0:
                return
        raise Exception("Missing at least one of tags, user_id and group_id")

    @staticmethod
    def fetch(call):
        logger.info("Making flickr API call: " + call)
        content = urllib2.urlopen(call).read()
        resp = json.loads(content)
        return resp

    @staticmethod
    def obtain_userid(url):
        logger.info("Fetching flickr user_id from URL: " + url)

        call = "http://api.flickr.com/services/rest/?method=flickr.urls.lookupUser&api_key=%s&url=%s&format=json&nojsoncallback=1" % (
            API_KEY,
            urllib.quote_plus(url))

        resp = FlickrDownloader.fetch(call)

        if resp["stat"] == "ok":
            logger.info("Found " + resp["user"]["id"])
            return True, "ok", resp["user"]["id"]
        else:
            logger.info("Oops " + resp["message"])
            return False, resp["message"], None

    @staticmethod
    def obtain_groupid(url):
        logger.info("Fetching flickr group_id from URL: " + url)

        call = "http://api.flickr.com/services/rest/?method=flickr.urls.lookupGroup&api_key=%s&url=%s&format=json&nojsoncallback=1" % (
            API_KEY,
            urllib.quote_plus(url))

        resp = FlickrDownloader.fetch(call)

        if resp["stat"] == "ok":
            logger.info("Found " + resp["group"]["id"])
            return True, "ok", resp["group"]["id"]
        else:
            logger.info("Oops " + resp["message"])
            return False, resp["message"], None

    def download_one(self):
        logger.info("Downloading an image from Flickr, " + self.location)
        logger.info("Queue size: %d" % len(self.queue))

        if not self.queue:
            self.fill_queue()

        urls = self.queue.pop()
        logger.info("Photo URL: " + urls[1])
        self.save_locally(urls[1], urls[0])

    def fill_queue(self):
        logger.info("Filling Flickr download queue: " + self.location)

        call = "http://api.flickr.com/services/rest/?method=flickr.photos.search" \
               "&api_key=%s&per_page=500&tag_mode=all&format=json&nojsoncallback=1" % API_KEY

        for k, v in self.params.items():
            call = call + "&" + k + "=" + v

        resp = FlickrDownloader.fetch(call)
        if resp["stat"] != "ok":
            raise Exception("Flickr returned error message: " + resp["message"])

        pages = int(resp["photos"]["pages"])
        page = random.randint(0, pages)
        logger.info("%d pages in the search results, using page %d" % (pages, page))

        call = call + "&extras=o_dims,url_o&page=" + str(page)
        resp = FlickrDownloader.fetch(call)
        if resp["stat"] != "ok":
            raise Exception("Flickr returned error message: " + resp["message"])

        for ph in resp["photos"]["photo"]:
            try:
                if not "url_o" in ph:
                    continue

                width = int(ph["width_o"])
                height = int(ph["height_o"])
                if width < 1000 or height < 800:
                    continue # skip small images

                original_url = ph["url_o"]
                photo_url = "http://www.flickr.com/photos/%s/%s" % (ph["owner"], ph["id"])
                self.queue.append((original_url, photo_url))
            except Exception:
                logger.exception("Error parsing single flickr photo info:")

        random.shuffle(self.queue)
        self.queue = self.queue[:len(self.queue)//2]
        # only use randomly half the images from the page -
        # if we ever hit that same page again, we'll still have what to download

        logger.info("Flickr queue populated with %d URLs" % len(self.queue))