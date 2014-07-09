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
import os

import logging
from urllib2 import HTTPError
import urlparse
from variety.Util import Util
from PIL import Image

from variety import _, _u

logger = logging.getLogger('variety')


class ImageFetcher:

    @staticmethod
    def url_ok(url, use_whitelist, hosts_whitelist):
        try:
            p = urlparse.urlparse(url)
            if p.scheme in ['http', 'https']:
                if use_whitelist:
                    for host in hosts_whitelist:
                        h = host.strip().lower()
                        if h and p.netloc.lower().find(h) >= 0:
                            return True
                else:
                    return p.path.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff'))
                    # skip gif - they are usually small images
            return False
        except Exception:
            return False

    @staticmethod
    def fetch(parent, url, to_folder, source_url=None, source_name=None, source_location=None, verbose=True):
        reported = verbose
        try:
            logger.info("Trying to fetch URL %s to %s " % (url, to_folder))
            if verbose:
                parent.show_notification(_("Fetching"), url)

            if url.startswith('javascript:'):
                if verbose:
                    parent.show_notification(_("Not an image"), url)
                return None

            if url.find('://') < 0:
                url = "file://" + url

            u = Util.urlopen(url)
            info = u.info()
            if not "content-type" in info:
                logger.info("Uknown content-type for url " + url)
                if verbose:
                    parent.show_notification(_("Not an image"), url)
                return None

            ct = info["content-type"]
            if not ct.startswith("image/"):
                logger.info("Unsupported content-type for url " + url + ": " + ct)
                if verbose:
                    parent.show_notification(_("Not an image"), url)
                return None

            local_name = Util.get_local_name(url)
            if "content-disposition" in info:
                cd = info["content-disposition"]
                cd_name = ImageFetcher.extract_filename_from_content_disposition(cd)
                if cd_name:
                    local_name = cd_name

            filename = os.path.join(to_folder, local_name)
            if os.path.exists(filename):
                m = Util.read_metadata(filename)
                if m and m.get("imageURL") == url:
                    logger.info("Local file already exists (%s)" % filename)
                    return filename
                else:
                    logger.info("File with same name already exists, but from different imageURL; renaming new download")
                    filename = Util.find_unique_name(filename)
                    local_name = os.path.basename(filename)

            logger.info("Fetching to " + filename)
            if not reported:
                reported = True
                parent.show_notification(_("Fetching"), url)

            data = u.read()
            with open(filename, 'wb') as f:
                f.write(data)

            try:
                img = Image.open(filename)
            except Exception:
                parent.show_notification(_("Not an image"), url)
                os.unlink(filename)
                return None

            if img.size[0] < 400 or img.size[1] < 400:
                # too small - delete and do not use
                parent.show_notification(_("Image too small, ignoring it"), url)
                os.unlink(filename)
                return None

            metadata = {"sourceName": source_name or "Fetched",
                        "sourceURL": source_url or url,
                        "imageURL": url}
            if source_location:
                metadata["sourceLocation"] = source_location
            Util.write_metadata(filename, metadata)

            logger.info("Fetched %s to %s." % (url, filename))

            return filename

        except Exception, e:
            logger.exception("Fetch failed for URL " + url)
            if reported:
                if isinstance(e, HTTPError) and e.code in (403, 404):
                    parent.show_notification(
                        _("Sorry, got %s error...") % str(e.code),
                        _("This means the link is no longer valid"))
                else:
                    parent.show_notification(
                        _("Fetch failed for some reason"),
                        _("To get more information, please run Variety from terminal with -v option and retry the action"))
            return None

    @staticmethod
    def extract_filename_from_content_disposition(cd):
        parts = cd.split(';')
        for p in parts:
            p = p.strip()
            if p.startswith("filename="):
                name = p[p.find('=') + 1:]
                if name[0] in ['"', "'"]:
                    name = name[1:]
                if name[-1] in ['"', "'"]:
                    name = name[:-1]
                return name
        return None
