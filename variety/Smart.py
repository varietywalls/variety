# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
# ## BEGIN LICENSE
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

from gi.repository import GObject
from urllib2 import HTTPError
from variety.Util import Util
from variety.Options import Options
from variety.SmartFeaturesNoticeDialog import SmartFeaturesNoticeDialog

from variety import _, _u

import os
import logging
import random
import json
import base64
import threading
import time

random.seed()
logger = logging.getLogger('variety')


class Smart:
    API_URL = "http://localhost:4000"

    def __init__(self, parent):
        self.parent = parent
        self.user = None

    def reload(self):
        self.load_user(create_if_missing=False)

    def first_run(self):
        if not self.parent.options.smart_notice_shown:
            self.show_notice_dialog()
        else:
            self.report_existing_favorites()

    def new_user(self):
        logger.info('Creating new smart user')
        self.user = Util.fetch_json(Smart.API_URL + '/newuser')
        if self.parent.preferences_dialog:
            GObject.idle_add(self.parent.preferences_dialog.on_smart_user_updated)
        with open(os.path.join(self.parent.config_folder, 'smart_user.json'), 'w') as f:
            json.dump(self.user, f, ensure_ascii=False, indent=2)
            logger.info('Created smart user: %s' % self.user["id"])

    def set_user(self, user):
        logger.info('Setting new smart user')
        self.user = user
        if self.parent.preferences_dialog:
            self.parent.preferences_dialog.on_smart_user_updated()
        with open(os.path.join(self.parent.config_folder, 'smart_user.json'), 'w') as f:
            json.dump(self.user, f, ensure_ascii=False, indent=2)
            logger.info('Updated smart user: %s' % self.user["id"])

    def load_user(self, create_if_missing=True, force_reload=False):
        if not self.user or force_reload:
            try:
                with open(os.path.join(self.parent.config_folder, 'smart_user.json')) as f:
                    self.user = json.load(f)
                    if self.parent.preferences_dialog:
                        self.parent.preferences_dialog.on_smart_user_updated()
                    logger.info('Loaded smart user: %s' % self.user["id"])
            except IOError:
                if create_if_missing:
                    logger.info('Missing user.json, creating new smart user')
                    self.new_user()

    def report_file(self, filename, tag, attempt=0):
        if not self.parent.options.smart_enabled:
            return -1

        try:
            self.load_user()

            meta = Util.read_metadata(filename)
            if not meta or not "sourceURL" in meta:
                return -2  # we only smart-report images coming from Variety online sources, not local images

            width, height = Util.get_size(filename)
            image = {
                'thumbnail': base64.b64encode(Util.get_thumbnail_data(filename, 300, 300)),
                'width': width,
                'height': height,
                'origin_url': meta['sourceURL'],
                'source_name': meta.get('sourceName', None),
                'source_location': meta.get('sourceLocation', None),
                'image_url': meta.get('imageURL', None)
            }

            logger.info("Smart-reporting %s as '%s'" % (filename, tag))
            try:
                url = Smart.API_URL + '/user/' + self.user['id'] + '/' + tag
                result = Util.fetch(url, {'image': json.dumps(image), 'authkey': self.user['authkey']})
                logger.info("Smart-reported, server returned: %s" % result)
                return 0
            except HTTPError, e:
                logger.error("Server returned %d, potential reason - server failure?" % e.code)
                if e.code in (403, 404):
                    self.parent.show_notification(
                        _('Your Smart Variety credentials are probably outdated. Please login again.'))
                    self.new_user()
                    self.parent.preferences_dialog.on_btn_login_register_clicked()

                if attempt == 3:
                    logger.exception(
                        "Could not smart-report %s as '%s, server error code %s'" % (filename, tag, e.code))
                    return -3
                return self.report_file(filename, tag, attempt + 1)
        except Exception:
            logger.exception("Could not smart-report %s as '%s'" % (filename, tag))
            return -4

    def show_notice_dialog(self):
        # Show Smart Variety notice
        dialog = SmartFeaturesNoticeDialog()

        def _on_ok(button):
            self.parent.options.smart_enabled = dialog.ui.enabled.get_active()
            self.parent.options.smart_notice_shown = True
            if self.parent.options.smart_enabled:
                for s in self.parent.options.sources:
                    if s[1] == Options.SourceType.RECOMMENDED:
                        self.parent.show_notification(_("Recommended source enabled"))
                        s[0] = True
            self.parent.options.write()
            self.parent.reload_config()
            dialog.destroy()
            self.parent.dialogs.remove(dialog)
            self.report_existing_favorites()

        dialog.ui.btn_ok.connect("clicked", _on_ok)
        self.parent.dialogs.append(dialog)
        dialog.run()

    def report_existing_favorites(self):
        if not self.parent.options.smart_enabled:
            return

        def _run():
            try:
                reportfile = os.path.join(self.parent.config_folder, '.unreported_favorites.txt')
                if not os.path.exists(reportfile):
                    logger.info("Listing existing favorites that need smart-reporting")
                    favs = []
                    for name in os.listdir(self.parent.options.favorites_folder):
                        path = os.path.join(self.parent.options.favorites_folder, name)
                        if Util.is_image(path) and Util.is_downloaded_by_variety(path):
                            logger.info("Existing favorite scheduled for smart-reporting: %s" % path)
                            favs.append(path)
                            time.sleep(0.1)
                    with open(reportfile, 'w') as f:
                        f.write('\n'.join(favs))
                else:
                    with open(reportfile) as f:
                        favs = [line.strip() for line in f.readlines()]

                for fav in list(favs):
                    if not self.parent.options.smart_enabled:
                        return
                    try:
                        logger.info("Smart-reporting existing favorite %s" % fav)
                        self.report_file(fav, "favorite")
                        favs.remove(fav)  # remove from list, no matter whether reporting suceeded or not
                        with open(reportfile, 'w') as f:
                            f.write('\n'.join(favs))
                        time.sleep(1)
                    except Exception:
                        logger.exception("Could not smart-report existing favorite %s" % fav)
            except Exception:
                logger.exception("Error while smart-reporting existing favorites")

        fav_report_thread = threading.Thread(target=_run)
        fav_report_thread.daemon = True
        fav_report_thread.start()
