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

import urllib.request, urllib.parse, urllib.error
import random
import logging
import time
from variety import Downloader
from variety.Util import Util

logger = logging.getLogger('variety')

random.seed()

API_KEY = "0553a848c09bcfd21d3a984d9408c04e"

class FlickrDownloader(Downloader.Downloader):
    last_download_time = 0

    def __init__(self, parent, location):
        super(FlickrDownloader, self).__init__(parent, "flickr", "Flickr", location)
        self.parse_location()
        self.queue = []
        self.last_fill_time = 0

    def convert_to_filename(self, url):
        return "flickr_" + super(FlickrDownloader, self).convert_to_filename(url)

    def parse_location(self):
        s = self.location.split(';')
        self.params = {}
        for x in s:
            if len(x) and x.find(':') > 0:
                k, v = x.split(':')
                if k.lower() in ["text", "tags", "user_id", "group_id"]:
                    self.params[k.lower()] = v.replace(' ', '+')

        # slight validation:
        for k in ["text", "tags", "user_id", "group_id"]:
            if k in self.params and len(self.params[k]) > 0:
                return
        raise Exception("Missing at least one of text, tags, user_id and group_id")

    @staticmethod
    def fetch(call):
        logger.info(lambda: "Making flickr API call: " + call)
        return Util.fetch_json(call)

    @staticmethod
    def obtain_userid(url):
        try:
            logger.info(lambda: "Fetching flickr user_id from URL: " + url)

            call = "https://api.flickr.com/services/rest/?method=flickr.urls.lookupUser&api_key=%s&url=%s&format=json&nojsoncallback=1" % (
                API_KEY,
                urllib.parse.quote_plus(url))

            resp = FlickrDownloader.fetch(call)

            if resp["stat"] == "ok":
                logger.info(lambda: "Found " + resp["user"]["id"])
                return True, "ok", resp["user"]["id"]
            else:
                logger.info(lambda: "Oops " + resp["message"])
                return False, resp["message"], None
        except Exception as e:
            logger.exception(lambda: "Exception while checking Flickr user")
            return False, "Exception while checking user. Please run with -v and check log.", None

    @staticmethod
    def obtain_groupid(url):
        try:
            logger.info(lambda: "Fetching flickr group_id from URL: " + url)

            call = "https://api.flickr.com/services/rest/?method=flickr.urls.lookupGroup&api_key=%s&url=%s&format=json&nojsoncallback=1" % (
                API_KEY,
                urllib.parse.quote_plus(url))

            resp = FlickrDownloader.fetch(call)

            if resp["stat"] == "ok":
                logger.info(lambda: "Found " + resp["group"]["id"])
                return True, "ok", resp["group"]["id"]
            else:
                logger.info(lambda: "Oops " + resp["message"])
                return False, resp["message"], None
        except Exception as e:
            logger.exception(lambda: "Exception while checking Flickr group")
            return False, "Exception while checking group. Please run with -v and check log.", None

    @staticmethod
    def count_search_results(search):
        try:
            dl = FlickrDownloader(None, search)
            return dl.count_results()
        except Exception:
            logger.exception(lambda: "Exception while counting Flickr results")
            return 0

    def count_results(self):
        call = "https://api.flickr.com/services/rest/?method=flickr.photos.search"\
               "&api_key=%s&per_page=20&tag_mode=all&format=json&nojsoncallback=1" % API_KEY

        for k, v in list(self.params.items()):
            call = call + "&" + k + "=" + v

        resp = FlickrDownloader.fetch(call)
        if resp["stat"] != "ok":
            raise Exception("Flickr returned error message: " + resp["message"])

        return int(resp["photos"]["total"])

    def download_one(self):
        min_download_interval, min_fill_queue_interval = self.parse_server_options("flickr", 60, 600)

        if time.time() - FlickrDownloader.last_download_time < min_download_interval:
            logger.info(lambda: "Minimal interval between Flickr downloads is %d, skip this attempt" % min_download_interval)
            return None

        logger.info(lambda: "Downloading an image from Flickr, " + self.location)
        logger.info(lambda: "Queue size: %d" % len(self.queue))

        if not self.queue:
            if time.time() - self.last_fill_time < min_fill_queue_interval:
                logger.info(lambda: "Flickr queue empty, but minimal interval between fill attempts is %d, will try again later" %
                            min_fill_queue_interval)
                return None

            self.fill_queue()

        if not self.queue:
            logger.info(lambda: "Flickr queue empty after fill - too restrictive search parameters or image size preference?")
            return None

        FlickrDownloader.last_download_time = time.time()

        urls = self.queue.pop()
        logger.info(lambda: "Photo URL: " + urls[0])
        return self.save_locally(urls[0], urls[1], extra_metadata=urls[2])

    def fill_queue(self):
        self.last_fill_time = time.time()

        logger.info(lambda: "Filling Flickr download queue: " + self.location)

        call = "https://api.flickr.com/services/rest/?method=flickr.photos.search" \
               "&api_key=%s&per_page=500&tag_mode=all&format=json&nojsoncallback=1" % API_KEY

        for k, v in list(self.params.items()):
            call = call + "&" + k + "=" + v

        resp = FlickrDownloader.fetch(call)
        if resp["stat"] != "ok":
            raise Exception("Flickr returned error message: " + resp["message"])

        pages = int(resp["photos"]["pages"])
        if pages < 1:
            return

        page = random.randint(1, pages)
        logger.info(lambda: "%d pages in the search results, using page %d" % (pages, page))

        call = call + "&extras=owner_name,description,tags,o_dims,url_o,url_k,url_h,url_l&page=" + str(page)
        resp = FlickrDownloader.fetch(call)
        if resp["stat"] != "ok":
            raise Exception("Flickr returned error message: " + resp["message"])

        used = set(x[0] for x in self.queue)
        size_suffixes = ["o", "k", "h", "l"]
        for s in size_suffixes:
            self.process_photos_in_response(resp, s, used)
            if len(self.queue) > 20:
                break

        random.shuffle(self.queue)
        if len(self.queue) >= 20:
            self.queue = self.queue[:len(self.queue)//2]
            # only use randomly half the images from the page -
            # if we ever hit that same page again, we'll still have what to download

        logger.info(lambda: "Flickr queue populated with %d URLs" % len(self.queue))

    def process_photos_in_response(self, resp, size_suffix, used):
        logger.info(lambda: "Queue size is %d, populating with images for size suffix %s" % (len(self.queue), size_suffix))
        for ph in resp["photos"]["photo"]:
            try:
                photo_url = "https://www.flickr.com/photos/%s/%s" % (ph["owner"], ph["id"])
                logger.debug(lambda: "Checking photo_url " + photo_url)

                if self.parent and photo_url in self.parent.banned:
                    logger.debug(lambda: "In banned, skipping")
                    continue
                if photo_url in used:
                    logger.debug(lambda: "Already added or checked, skipping")
                    continue

                if "url_" + size_suffix in ph:
                    width = int(ph["width_" + size_suffix])
                    height = int(ph["height_" + size_suffix])
                    image_file_url = ph["url_" + size_suffix]
                    logger.debug(lambda: "Image url: " + image_file_url)
                else:
                    logger.debug(lambda: "Missing size " + size_suffix)
                    continue

                # add to used now - if one of the checks below fails, we don't want the lower resolutions either
                used.add(photo_url)

                if self.is_in_downloaded(image_file_url):
                    logger.debug(lambda: "Already in downloaded")
                    continue

                if self.is_in_favorites(image_file_url):
                    logger.debug(lambda: "Already in favorites")
                    continue

                if self.parent and not self.parent.size_ok(width, height):
                    logger.debug(lambda: "Small or non-landscape size/resolution")
                    continue

                try:
                    extra_metadata = {
                        'author': ph['ownername'],
                        'authorURL': 'https://www.flickr.com/photos/%s' % ph["owner"],
                        'headline': ph['title'],
                        'keywords': ph['tags'].split(' '),
                        'description': ph['description']['_content']
                    }
                except:
                    extra_metadata = {}

                logger.debug(lambda: "Appending to queue %s, %s" % (photo_url, image_file_url))
                self.queue.append((photo_url, image_file_url, extra_metadata))
            except Exception:
                logger.exception(lambda: "Error parsing single flickr photo info:")

    @staticmethod
    def get_photo_id(origin_url):
        if origin_url[-1] == '/':
            origin_url = origin_url[:-1]
        return origin_url.split('/')[-1]

    @staticmethod
    def get_image_url(origin_url):
        photo_id = FlickrDownloader.get_photo_id(origin_url)
        call = 'https://api.flickr.com/services/rest/?method=flickr.photos.getSizes&api_key=%s&photo_id=%s&format=json&nojsoncallback=1' % \
               (API_KEY, photo_id)
        resp = Util.fetch_json(call)
        s = max(resp['sizes']['size'], key=lambda size: int(size['width']))
        return s['source']

    @staticmethod
    def get_extra_metadata(origin_url):
        photo_id = FlickrDownloader.get_photo_id(origin_url)
        call = 'https://api.flickr.com/services/rest/?method=flickr.photos.getInfo&api_key=%s&photo_id=%s&format=json&nojsoncallback=1' % \
               (API_KEY, photo_id)
        resp = Util.fetch_json(call)
        ph = resp['photo']
        extra_meta = {
            'headline': ph['title']['_content'],
            'description': ph['description']['_content'],
            'author': ph['owner']['realname'],
            'authorURL': 'https://www.flickr.com/photos/%s' % ph['owner']['nsid'],
            'keywords': [x['_content'] for x in ph['tags']['tag']],
        }
        return extra_meta

