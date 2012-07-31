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
import os

import urllib2
import logging
import urlparse
from variety.Util import Util

logger = logging.getLogger('variety')


class ImageFetcher:

    @staticmethod
    def url_ok(url, hosts_whitelist):
        try:
            p = urlparse.urlparse(url)
            if p.scheme in ['http', 'https']:
                for host in hosts_whitelist:
                    if host.strip() and p.netloc.find(host) >= 0:
                        return True
            return False
        except Exception:
            return False

    @staticmethod
    def fetch(parent, url, to, verbose = True):
        reported = verbose
        try:
            logger.info("Trying to fetch URL %s to %s " % (url, to))
            if verbose:
                parent.show_notification("Fetching", url)

            if url.startswith('javascript:'):
                if verbose:
                    parent.show_notification("Not an image", url)
                return None

            if url.find('://') < 0:
                url = "file://" + url

            u = urllib2.urlopen(url, timeout=20)
            info = u.info()
            if not "content-type" in info:
                logger.info("Uknown content-type for url " + url)
                if verbose:
                    parent.show_notification("Not an image", url)
                return None

            ct = info["content-type"]
            if not ct.startswith("image/"):
                logger.info("Unsupported content-type for url " + url + ": " + ct)
                if verbose:
                    parent.show_notification("Not an image", url)
                return None

            local_name = Util.get_local_name(url)
            if "content-disposition" in info:
                cd = info["content-disposition"]
                cd_name = ImageFetcher.extract_filename_from_content_disposition(cd)
                if cd_name:
                    local_name = cd_name

            filename = os.path.join(to, local_name)
            if os.path.exists(filename):
                logger.info("Local file already exists (%s)" % filename)
                parent.show_notification("Fetched", "%s\nPress Next to see it" % local_name)
                return filename

            logger.info("Fetching to " + filename)
            if not reported:
                reported = True
                parent.show_notification("Fetching", url)

            data = u.read()
            localFile = open(filename, 'wb')
            localFile.write(data)
            localFile.close()

            logger.info("Fetched %s to %s." % (url, filename))
            parent.show_notification("Fetched", "%s\nPress Next to see it" % local_name)

            return filename

        except Exception:
            logger.exception("Fetch failed for URL " + url)
            if reported:
                parent.show_notification("Fetch failed for some reason", "You may check the log if running in terminal with -v option")
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
