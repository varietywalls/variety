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
import hashlib
from urllib2 import HTTPError
import io
from variety.Util import Util
from variety.Options import Options
from variety.SmartFeaturesNoticeDialog import SmartFeaturesNoticeDialog
from variety.AttrDict import AttrDict
from variety.ImageFetcher import ImageFetcher

from variety import _, _u

import os
import logging
import random
import json
import base64
import threading
import time
import sys

random.seed()
logger = logging.getLogger('variety')


class Smart:
    SITE_URL = 'http://localhost:4000' if '--debug-smart' in sys.argv else 'https://vrty.org'
    API_URL = SITE_URL + '/api'

    def __init__(self, parent):
        self.parent = parent
        self.user = None

    def reload(self):
        if self.smart_settings_changed():
            self.load_user(create_if_missing=False, force_reload=True)
            self.reset_sync()
            self.sync()

    def smart_settings_changed(self):
        return self.parent.previous_options is None or \
               self.parent.previous_options.smart_enabled != self.parent.options.smart_enabled or \
               self.parent.previous_options.sync_enabled != self.parent.options.sync_enabled or \
               self.parent.previous_options.favorites_folder != self.parent.options.favorites_folder

    def first_run(self):
        if not self.parent.options.smart_notice_shown:
            self.show_notice_dialog()

    def new_user(self):
        logger.info('Creating new smart user')

        self.reset_sync()

        self.user = Util.fetch_json(Smart.API_URL + '/newuser')
        if self.parent.preferences_dialog:
            GObject.idle_add(self.parent.preferences_dialog.on_smart_user_updated)
        with open(os.path.join(self.parent.config_folder, 'smart_user.json'), 'w') as f:
            json.dump(self.user, f, ensure_ascii=False, indent=2)
            logger.info('Created smart user: %s' % self.user["id"])

    def reset_sync(self):
        self.sync_hash = Util.random_hash()  #  stop current sync if running
        self.last_synced = 0

    def set_user(self, user):
        logger.info('Setting new smart user')

        self.user = user
        if self.parent.preferences_dialog:
            self.parent.preferences_dialog.on_smart_user_updated()
        with open(os.path.join(self.parent.config_folder, 'smart_user.json'), 'w') as f:
            json.dump(self.user, f, ensure_ascii=False, indent=2)
            logger.info('Updated smart user: %s' % self.user["id"])

        self.reset_sync()
        self.sync()

    def load_user(self, create_if_missing=True, force_reload=False):
        if not self.user or force_reload:
            self.user = None
            try:
                with open(os.path.join(self.parent.config_folder, 'smart_user.json')) as f:
                    self.user = json.load(f)
                    if self.parent.preferences_dialog:
                        self.parent.preferences_dialog.on_smart_user_updated()
                    logger.info('Loaded smart user: %s' % self.user["id"])
            except IOError:
                if create_if_missing:
                    logger.info('Missing smart_user.json, creating new smart user')
                    self.new_user()

    def report_trash(self, origin_url):
        if not self.is_smart_enabled():
            return

        try:
            self.load_user()
            user = self.user

            logger.info("Smart-reporting %s as trash" % origin_url)
            try:
                url = Smart.API_URL + '/tag/' + user['id'] + '/trash'
                result = Util.fetch(url, {'image': json.dumps({'origin_url': origin_url}), 'authkey': user['authkey']})
                logger.info("Smart-reported, server returned: %s" % result)
                return

            except HTTPError, e:
                logger.error("Server returned %d, potential reason - server failure?" % e.code)
                if e.code in (403, 404):
                    self.parent.show_notification(
                        _('Your Smart Variety credentials are probably outdated. Please login again.'))
                    self.new_user()
                    self.parent.preferences_dialog.on_btn_login_register_clicked()

        except Exception:
            logger.exception("Could not smart-report %s as trash" % url)

    def report_file(self, filename, tag, async=True, upload_full_image=False):
        if not async:
            self._do_report_file(filename, tag, upload_full_image=upload_full_image)
        else:
            def _go():
                self._do_report_file(filename, tag, upload_full_image=upload_full_image)
            threading.Timer(0, _go).start()

    def _do_report_file(self, filename, tag, attempt=0, upload_full_image=False):
        if not self.is_smart_enabled():
            return

        try:
            self.load_user()
            user = self.user

            meta = Util.read_metadata(filename)
            if not meta or not "sourceURL" in meta:
                return  # we only smart-report images coming from Variety online sources, not local images

            width, height = Util.get_size(filename)
            image = {
                'thumbnail': base64.b64encode(Util.get_thumbnail_data(filename, 600, 450)),
                'width': width,
                'height': height,
                'filename': os.path.basename(filename),
                'origin_url': meta['sourceURL'],
                'source_name': meta.get('sourceName', None),
                'source_location': meta.get('sourceLocation', None),
                'image_url': meta.get('imageURL', None)
            }

            # check for dead links and upload full image in that case (happens with old favorites):
            if upload_full_image or (tag == 'favorite' and not Util.is_working_image_link(meta.get('imageURL', None))):
                with open(filename, 'r') as f:
                    image['full_image'] = base64.b64encode(f.read())

            logger.info("Smart-reporting %s as '%s'" % (filename, tag))
            try:
                url = Smart.API_URL + '/tag/' + user['id'] + '/' + tag
                result = Util.fetch(url, {'image': json.dumps(image), 'authkey': user['authkey']})
                logger.info("Smart-reported, server returned: %s" % result)
                return
            except HTTPError, e:
                logger.error("Server returned %d, potential reason - server failure?" % e.code)
                if e.code in (403, 404):
                    self.parent.show_notification(
                        _('Your Smart Variety credentials are probably outdated. Please login again.'))
                    self.new_user()
                    self.parent.preferences_dialog.on_btn_login_register_clicked()

                if attempt < 3:
                    self._do_report_file(filename, tag, attempt + 1)
                else:
                    logger.exception("Could not smart-report %s as '%s, server error code %s'" % (filename, tag, e.code))
        except Exception:
            logger.exception("Could not smart-report %s as '%s'" % (filename, tag))

    def show_notice_dialog(self):
        # Show Smart Variety notice
        dialog = SmartFeaturesNoticeDialog()

        def _on_ok(button):
            self.parent.options.smart_enabled = dialog.ui.enabled.get_active()
            self.parent.options.smart_notice_shown = True
            if self.parent.options.smart_enabled:
                for s in self.parent.options.sources:
                    if s[1] in (Options.SourceType.RECOMMENDED, Options.SourceType.LATEST):
                        self.parent.show_notification(_("New image sources"),
                                                      _("Recommended and Latest Favorites image sources enabled"))
                        s[0] = True
            self.parent.options.write()
            self.parent.reload_config()
            dialog.destroy()
            self.parent.dialogs.remove(dialog)
            self.sync()

        dialog.ui.btn_ok.connect("clicked", _on_ok)
        self.parent.dialogs.append(dialog)
        dialog.run()

    def load_syncdb(self):
        logger.debug("sync: Loading syncdb")
        syncdb_file = os.path.join(self.parent.config_folder, 'syncdb.json')
        try:
            with io.open(syncdb_file, encoding='utf8') as f:
                data = f.read()
                syncdb = AttrDict(json.loads(data))
        except:
            syncdb = AttrDict(version=1, local={}, remote={})

        return syncdb

    def write_syncdb(self, syncdb):
        syncdb_file = os.path.join(self.parent.config_folder, 'syncdb.json')
        with io.open(syncdb_file, "w", encoding='utf8') as f:
            f.write(json.dumps(syncdb.asdict(), indent=4, ensure_ascii=False))

    @staticmethod
    def get_image_id(url):
        return base64.urlsafe_b64encode(hashlib.md5(url).digest())[:10].replace('-', 'a').replace('_', 'b').lower()

    def is_smart_enabled(self):
        return self.parent.options.smart_notice_shown and self.parent.options.smart_enabled

    def is_sync_enabled(self):
        return self.is_smart_enabled() and \
               self.user is not None and self.user.get("username") is not None and \
               self.parent.options.sync_enabled

    def sync(self):
        if not self.is_smart_enabled():
            return

        self.sync_hash = Util.random_hash()
        current_sync_hash = self.sync_hash

        def _run():
            logger.info('sync: Started, hash %s' % current_sync_hash)

            try:
                self.load_user(create_if_missing=True)

                logger.info("sync: Fetching serverside data")
                server_data = AttrDict(Util.fetch_json(Smart.API_URL + '/user/' + self.user["id"] + '/sync'))

                syncdb = self.load_syncdb()

                # First upload local favorites that need uploading:
                logger.info("sync: Uploading local favorites to server")
                for name in os.listdir(self.parent.options.favorites_folder):
                    try:
                        if not self.is_smart_enabled() or current_sync_hash != self.sync_hash:
                            return

                        time.sleep(0.1)

                        path = os.path.join(self.parent.options.favorites_folder, name)
                        if not Util.is_image(path):
                            continue

                        if path in syncdb.local:
                            info = syncdb.local[path]
                        else:
                            info = {}
                            source_url = Util.get_variety_source_url(path)
                            if source_url:
                                info["sourceURL"] = source_url
                            syncdb.local[path] = info
                            self.write_syncdb(syncdb)

                        if not "sourceURL" in info:
                            continue

                        imageid = self.get_image_id(info["sourceURL"])
                        if not "success" in syncdb.remote[imageid]:
                            syncdb.remote[imageid] = {"success": True}
                            self.write_syncdb(syncdb)

                        if not imageid in server_data["favorite"]:
                            logger.info("sync: Smart-reporting existing favorite %s" % path)
                            self.report_file(path, "favorite", async=False)
                            time.sleep(1)
                    except:
                        logger.exception("sync: Could not process file %s" % name)

                # Upload locally trashed URLs
                logger.info("sync: Uploading local banned URLs to server")
                for url in self.parent.banned:
                    if not self.is_smart_enabled() or current_sync_hash != self.sync_hash:
                        return
                    imageid = self.get_image_id(url)
                    if not imageid in server_data["trash"]:
                        self.report_trash(url)
                        time.sleep(1)

                # Perform server to local downloading only if Sync is enabled
                if self.is_sync_enabled():

                    # Append locally missing trashed URLs to banned list
                    local_trash = map(self.get_image_id, self.parent.banned)
                    for imageid in server_data["trash"]:
                        if not self.is_sync_enabled() or current_sync_hash != self.sync_hash:
                            return
                        if not imageid in local_trash:
                            image_data = Util.fetch_json(Smart.API_URL + '/image/' + imageid)
                            self.parent.ban_url(image_data["origin_url"])

                    # Download locally-missing favorites from the server
                    to_sync = []
                    for imageid in server_data["favorite"]:
                        if imageid in server_data["trash"]:
                            continue  # do not download favorites that have later been trashed;
                            # TODO: we need a better way to un-favorite things and forbid them from downloading

                        if imageid in syncdb.remote:
                            if 'success' in syncdb.remote[imageid]:
                                continue  # we have this image locally
                            if syncdb.remote[imageid].get('error', 0) >= 3:
                                continue  # we have tried and got error for this image 3 or more times, leave it alone
                        to_sync.append(imageid)

                    if to_sync:
                        self.parent.show_notification(_("Sync"), _("Fetching %d images") % len(to_sync))

                    for imageid in to_sync:
                        if not self.is_sync_enabled() or current_sync_hash != self.sync_hash:
                            return

                        try:
                            logger.info("sync: Downloading locally-missing favorite image %s" % imageid)
                            image_data = Util.fetch_json(Smart.API_URL + '/image/' + imageid)

                            path = ImageFetcher.fetch(image_data["image_url"], self.parent.options.favorites_folder,
                                               source_url=image_data["origin_url"],
                                               source_name=image_data["sources"][0][0] if image_data.get("sources", []) else None,
                                               source_location=image_data["sources"][0][1] if image_data.get("sources", []) else None,
                                               verbose=False)
                            if not path:
                                raise Exception("Fetch failed")

                            syncdb.remote[imageid] = {"success": True}
                            syncdb.local[path] = {'sourceURL': image_data["origin_url"]}

                        except:
                            logger.exception("sync: Could not fetch favorite image %s" % imageid)
                            syncdb.remote[imageid] = syncdb.remote[imageid] or {}
                            syncdb.remote[imageid].setdefault("error", 0)
                            syncdb.remote[imageid]["error"] += 1

                        finally:
                            if not self.is_smart_enabled() or current_sync_hash != self.sync_hash:
                                return

                            self.write_syncdb(syncdb)
                            time.sleep(1)

                    if to_sync:
                        self.parent.show_notification(_("Sync"), _("Finished"))

                self.last_synced = time.time()
            finally:
                self.syncing = False

        sync_thread = threading.Thread(target=_run)
        sync_thread.daemon = True
        sync_thread.start()

    def sync_if_its_time(self):
        if not self.is_smart_enabled():
            return
        last_synced = getattr(self, 'last_synced', 0)
        if time.time() - last_synced > 6 * 60 * 3600:
            self.sync()