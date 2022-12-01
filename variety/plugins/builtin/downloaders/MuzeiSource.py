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

from variety.Util import Util, _
from variety.plugins.downloaders.SimpleDownloader import SimpleDownloader

DATA_URL = "https://muzeiapi.appspot.com/featured"

logger = logging.getLogger("variety")

random.seed()


class MuzeiDownloader(SimpleDownloader):
    DESCRIPTION = _("Muzei Featured Arts")
    ROOT_URL = "https://www.wikiart.org"

    @classmethod
    def get_info(cls):
        return {
            "name": "MuzeiDownloader",
            "description": MuzeiDownloader.DESCRIPTION,
            "author": "Gergely Kontra",
            "version": "0.1",
        }

    def get_description(self):
        return MuzeiDownloader.DESCRIPTION

    def get_source_type(self):
        return "muzei"

    def get_source_name(self):
        return "Muzei Featured Art"

    def get_source_location(self):
        return self.ROOT_URL

    def fill_queue(self):
        queue = Util.fetch_json(DATA_URL)
        return [queue]

    def download_queue_item(self, item):
        print('item', item)
        _, filename = item["imageUri"].rsplit('/', 1)
        extra_metadata = {"author": item["byline"]}

        return self.save_locally(
            item["detailsUri"], item["imageUri"],
            extra_metadata=extra_metadata,
            local_filename=filename,
            source_location=item["detailsUri"],
            source_name="WikiArt"
        )
