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
import os
import urllib.parse

from PIL import Image
from requests.exceptions import HTTPError

from variety.Util import Util, _

logger = logging.getLogger("variety")


class ImageFetcher:
    @staticmethod
    def url_ok(url, use_whitelist, hosts_whitelist):
        try:
            p = urllib.parse.urlparse(url)
            if p.scheme in ["http", "https"]:
                if use_whitelist:
                    for host in hosts_whitelist:
                        h = host.strip().lower()
                        if h and p.netloc.lower().find(h) >= 0:
                            return True
                else:
                    return p.path.lower().endswith((".jpg", ".jpeg", ".png", ".tiff", ".avif", ".webp"))
                    # skip gif - they are usually small images
            return False
        except Exception:
            return False

    @staticmethod
    def fetch(
        url,
        to_folder,
        origin_url=None,
        source_type=None,
        source_location=None,
        source_name=None,
        extra_metadata=None,
        progress_reporter=lambda a, b: None,
        verbose=True,
    ):
        reported = verbose
        try:
            logger.info(lambda: "Trying to fetch URL %s to %s " % (url, to_folder))
            if verbose:
                progress_reporter(_("Fetching"), url)

            if url.startswith("javascript:"):
                if verbose:
                    progress_reporter(_("Not an image"), url)
                return None

            if url.find("://") < 0:
                url = "file://" + url

            r = Util.request(url, stream=True)
            if not "content-type" in r.headers:
                logger.info(lambda: "Unknown content-type for url " + url)
                if verbose:
                    progress_reporter(_("Not an image"), url)
                return None

            ct = r.headers["content-type"]
            if not ct.startswith("image/"):
                logger.info(lambda: "Unsupported content-type for url " + url + ": " + ct)
                if verbose:
                    progress_reporter(_("Not an image"), url)
                return None

            local_name = Util.get_local_name(r.url)
            if "content-disposition" in r.headers:
                cd = r.headers["content-disposition"]
                cd_name = ImageFetcher.extract_filename_from_content_disposition(cd)
                if cd_name:
                    local_name = cd_name

            filename = os.path.join(to_folder, local_name)
            if os.path.exists(filename):
                m = Util.read_metadata(filename)
                if m and m.get("imageURL") == url:
                    logger.info(lambda: "Local file already exists (%s)" % filename)
                    return filename
                else:
                    logger.info(
                        lambda: "File with same name already exists, but from different imageURL; renaming new download"
                    )
                    filename = Util.find_unique_name(filename)

            logger.info(lambda: "Fetching to " + filename)
            if not reported:
                reported = True
                progress_reporter(_("Fetching"), url)

            local_filepath_partial = filename + ".partial"
            with open(local_filepath_partial, "wb") as f:
                Util.request_write_to(r, f)

            try:
                img = Image.open(local_filepath_partial)
            except Exception:
                progress_reporter(_("Not an image"), url)
                Util.safe_unlink(local_filepath_partial)
                return None

            if img.size[0] < 400 or img.size[1] < 400:
                # too small - delete and do not use
                progress_reporter(_("Image too small, ignoring it"), url)
                Util.safe_unlink(local_filepath_partial)
                return None

            metadata = {
                "sourceType": source_type or "fetched",
                "sourceName": source_name or "Fetched",
                "sourceURL": origin_url or url,
                "imageURL": url,
            }
            if source_location:
                metadata["sourceLocation"] = source_location
            metadata.update(extra_metadata or {})
            Util.write_metadata(local_filepath_partial, metadata)

            os.rename(local_filepath_partial, filename)
            logger.info(lambda: "Fetched %s to %s." % (url, filename))
            return filename

        except Exception as e:
            # pylint: disable=no-member
            logger.exception(lambda: "Fetch failed for URL " + url)
            if reported:
                if isinstance(e, HTTPError) and e.response.status_code in (403, 404):
                    progress_reporter(
                        _("Sorry, got %s error...") % str(e.response.status_code),
                        _("This means the link is no longer valid"),
                    )
                else:
                    progress_reporter(
                        _("Fetch failed for some reason"),
                        _(
                            "To get more information, please run Variety from terminal with -v option and retry the action"
                        ),
                    )
            return None

    @staticmethod
    def extract_filename_from_content_disposition(cd):
        parts = cd.split(";")
        for p in parts:
            p = p.strip()
            if p.startswith("filename="):
                name = p[p.find("=") + 1 :]
                if name[0] in ['"', "'"]:
                    name = name[1:]
                if name[-1] in ['"', "'"]:
                    name = name[:-1]
                return name
        return None
