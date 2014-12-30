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

from gi.repository import GObject, Gdk, Gtk
import hashlib
from urllib2 import HTTPError
import io
import webbrowser
from variety.Util import Util, throttle
from variety.Options import Options
from variety.SmartFeaturesNoticeDialog import SmartFeaturesNoticeDialog
from variety.SmartRegisterDialog import SmartRegisterDialog
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

    META_KEYS_MAP = {
        'sourceURL': 'origin_url',
        'imageURL': 'image_url',
        'sourceType': 'source_type',
        'sourceLocation': 'source_location',
        'sourceName': 'source_name',
        'authorURL': 'author_url',
        'sfwRating': 'sfw_rating',
    }

    def __init__(self, parent):
        self.parent = parent
        self.user = None

    def reload(self):
        if not self.is_smart_enabled():
            self._reset_sync()
            return

        try:
            if self.smart_settings_changed():
                self.load_user(create_if_missing=False, force_reload=True)
                self.sync()
            elif self.parent.previous_options.sources != self.parent.options.sources:
                self.sync_sources(in_thread=True)
        except:
            logger.exception("Smart: Exception in reload:")

    def get_profile_url(self):
        if self.user:
            return "%s/login/%s?authkey=%s" % (Smart.SITE_URL, self.user["id"], self.user.get('authkey', ''))
        else:
            return None

    def get_register_url(self, source):
        if self.user:
            return '%s/user/%s/register?authkey=%s&source=%s' % (Smart.SITE_URL, self.user['id'], self.user['authkey'], source)
        else:
            return '%s/register?source=%s' % (Smart.SITE_URL, source)

    def smart_settings_changed(self):
        return self.parent.previous_options is None or \
               self.parent.previous_options.smart_enabled != self.parent.options.smart_enabled or \
               self.parent.previous_options.sync_enabled != self.parent.options.sync_enabled or \
               self.parent.previous_options.favorites_folder != self.parent.options.favorites_folder

    def load_user(self, create_if_missing=True, force_reload=False):
        if not self.user or force_reload:
            self.user = None
            try:
                with io.open(os.path.join(self.parent.config_folder, 'smart_user.json'), encoding='utf8') as f:
                    data = f.read()
                    self.user = AttrDict(json.loads(data))
                    if self.parent.preferences_dialog:
                        self.parent.preferences_dialog.on_smart_user_updated()
                    logger.info('smart: Loaded smart user: %s' % self.user["id"])
            except IOError:
                if create_if_missing:
                    logger.info('smart: Missing smart_user.json, creating new smart user')
                    self.new_user()

    def new_user(self):
        logger.info('smart: Creating new smart user')

        self._reset_sync()

        self.user = Util.fetch_json(Smart.API_URL + '/newuser')
        self.save_user()
        if self.parent.preferences_dialog:
            GObject.idle_add(self.parent.preferences_dialog.on_smart_user_updated)
        logger.info('smart: Created smart user: %s' % self.user["id"])

    def save_user(self):
        with io.open(os.path.join(self.parent.config_folder, 'smart_user.json'), 'w', encoding='utf8') as f:
            f.write(json.dumps(self.user, indent=4, ensure_ascii=False, encoding='utf8'))

    def set_user(self, user):
        logger.info('smart: Setting new smart user')

        # keep machine-dependent settings from current user
        if self.user:
            for key in ("machine_id", "machine_label"):
                if key in self.user:
                    user[key] = self.user[key]

        self.user = user

        if self.parent.preferences_dialog:
            GObject.idle_add(self.parent.preferences_dialog.on_smart_user_updated)

        with open(os.path.join(self.parent.config_folder, 'smart_user.json'), 'w') as f:
            json.dump(self.user, f, ensure_ascii=False, indent=2)
            logger.info('smart: Updated smart user: %s' % self.user["id"])

        self.sync()

    def report_trash(self, origin_url):
        if not self.is_smart_enabled():
            return

        try:
            self.load_user()
            user = self.user

            logger.info("smart: Reporting %s as trash" % origin_url)
            try:
                url = Smart.API_URL + '/upload/' + user['id'] + '/trash'
                result = Util.fetch(url, {'image': json.dumps({'origin_url': origin_url}), 'authkey': user['authkey']})
                logger.info("smart: Reported, server returned: %s" % result)
                return

            except HTTPError, e:
                self.handle_user_http_error(e)

        except Exception:
            logger.exception("smart: Could not report %s as trash" % url)

    def report_file(self, filename, mark, async=True, upload_full_image=False, needs_reupload=False):
        if not self.is_smart_enabled():
            return

        def _go():
            self._do_report_file(filename, mark, upload_full_image=upload_full_image, needs_reupload=needs_reupload)

        _go() if not async else threading.Timer(0, _go).start()

    def handle_user_http_error(self, e):
        logger.error("smart: Server returned %d, potential reason - server failure?" % e.code)
        if e.code in (403, 404):
            self.parent.show_notification(
                _('Your VRTY.ORG credentials are probably outdated. Please login again.'))
            Util.add_mainloop_task(self.parent.preferences_dialog.on_btn_login_register_clicked)
            raise e

    @staticmethod
    def fix_origin_url(origin_url):
        if origin_url and '//picasaweb.google.com' in origin_url and '?' in origin_url:
            origin_url = origin_url[:origin_url.rindex('?')]
        return origin_url

    @staticmethod
    def fill_missing_meta_info(filename, meta):
        try:
            if 'imageURL' not in meta:
                image_url = Util.guess_image_url(meta)
                if image_url:
                    meta['imageURL'] = image_url
                    Util.write_metadata(filename, meta)

            if 'sourceType' not in meta:
                source_type = Util.guess_source_type(meta)
                if source_type:
                    meta['sourceType'] = source_type
                    Util.write_metadata(filename, meta)

            if 'headline' not in meta:
                origin_url = meta['sourceURL']
                if 'flickr.com' in origin_url:
                    from variety.FlickrDownloader import FlickrDownloader
                    extra_meta = FlickrDownloader.get_extra_metadata(origin_url)
                    meta.update(extra_meta)
                    Util.write_metadata(filename, meta)


        except:
            logger.exception('Could not fill missing meta-info')

    def _do_report_file(self, filename, mark, attempt=1, upload_full_image=False, needs_reupload=False):
        if not self.is_smart_enabled():
            return

        try:
            self.load_user()
            user = self.user

            meta = Util.read_metadata(filename)
            if not meta or not "sourceURL" in meta:
                return  # we only smart-report images coming from Variety online sources, not local images

            origin_url = Smart.fix_origin_url(meta['sourceURL'])

            if not (upload_full_image or needs_reupload):
                # Attempt quick-markging using just the computed image ID - will only succeed if the image already exists on the server
                try:
                    logger.info("smart: Quick-reporting %s as '%s'" % (filename, mark))
                    imageid = self.get_image_id(origin_url)
                    report_url = Smart.API_URL + '/mark/%s/%s/+%s' % (user['id'], imageid, mark)
                    result = Util.fetch(report_url, {'authkey': user['authkey']})
                    logger.info("smart: Quick-reported, server returned: %s" % result)
                    return
                except:
                    logger.info("smart: Image uknown to server, performing full report")

            width, height = Util.get_size(filename)

            Smart.fill_missing_meta_info(filename, meta)

            image_url = meta.get('imageURL', None)
            image = {
                'thumbnail': base64.b64encode(Util.get_thumbnail_data(filename, 1024, 1024)),
                'width': width,
                'height': height,
                'filename': os.path.basename(filename),
                'origin_url': origin_url,
                'image_url': image_url,
            }

            for key, value in meta.items():
                server_key = Smart.META_KEYS_MAP.get(key, key)
                if not server_key in image:
                    image[server_key] = value

            logger.info("smart: Reporting %s as '%s'" % (filename, mark))

            # check for dead links and upload full image in that case (happens with old favorites):
            if upload_full_image or (mark == 'favorite' and Util.is_dead_or_not_image(image_url)):
                if upload_full_image:
                    logger.info('smart: Including full image in upload per server request')
                else:
                    logger.info('smart: Including full image in upload as image link seems dead: %s, sourceURL: %s' %
                                (image_url, origin_url))
                with open(filename, 'r') as f:
                    image['full_image'] = base64.b64encode(f.read())

            report_url = Smart.API_URL + '/upload/%s/%s' % (user['id'], mark)
            try:
                result = Util.fetch(report_url, {'image': json.dumps(image), 'authkey': user['authkey']})
                logger.info("smart: Reported, server returned: %s" % result)
                return
            except HTTPError, e:
                self.handle_user_http_error(e)

                if attempt == 1:
                    self._do_report_file(filename, mark, attempt + 1)
                else:
                    logger.exception("smart: Could not report %s as '%s, server error code %s'" % (filename, mark, e.code))
        except Exception:
            logger.exception("smart: Could not report %s as '%s'" % (filename, mark))

    def show_notice_dialog(self):
        # Show Smart Variety notice
        dialog = SmartFeaturesNoticeDialog()

        def _on_ok(button):
            self.parent.options.smart_enabled = dialog.ui.smart_enabled.get_active()

            self.parent.options.smart_notice_shown = True
            if self.parent.options.smart_enabled:
                for s in self.parent.options.sources:
                    if s[1] in (Options.SourceType.RECOMMENDED,):
                        s[0] = True

            self.parent.options.write()
            self.parent.reload_config()
            dialog.destroy()
            self.parent.dialogs.remove(dialog)

        dialog.ui.btn_ok.connect("clicked", _on_ok)
        self.parent.dialogs.append(dialog)
        dialog.run()

    def show_register_dialog(self):
        self.load_user(create_if_missing=False)
        if self.is_registered():
            self.parent.options.smart_register_shown = True
            self.parent.options.write()
            return

        self.register_dialog = SmartRegisterDialog()

        def _register_link(*args):
            try:
                self.load_user(create_if_missing=True)
            except IOError:
                self.parent.show_notification(_('Could not connect'),
                                              _('Oosp, we could not connect to VRTY.ORG. Server might be down.\n\n'
                                                'Please wait a couple of minutes and try again or register later '
                                                'from the "Sync and social" page in Preferences.'))
            webbrowser.open_new_tab(self.get_register_url('variety_register_dialog'))
        self.register_dialog.ui.btn_register.connect('activate-link', _register_link)

        self.parent.dialogs.append(self.register_dialog)

        self.register_dialog.run()
        result = self.register_dialog.result

        try:
            self.parent.dialogs.remove(self.register_dialog)
        except:
            pass
        self.register_dialog.destroy()
        self.register_dialog = None
        if not self.parent.running:
            return

        self.parent.options.smart_register_shown = True
        self.parent.options.write()

        if result == 'login':
            self.parent.preferences_dialog.on_btn_login_register_clicked()

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

    @throttle(seconds=5, trailing_call=True)
    def write_syncdb(self, syncdb):
        syncdb_file = os.path.join(self.parent.config_folder, 'syncdb.json')
        with io.open(syncdb_file, "w", encoding='utf8') as f:
            f.write(json.dumps(syncdb.asdict(), indent=4, ensure_ascii=False, encoding='utf8'))

    @staticmethod
    def get_image_id(url):
        return base64.urlsafe_b64encode(hashlib.md5(url).digest())[:10].replace('-', 'a').replace('_', 'b').lower()

    def is_smart_enabled(self):
        return self.parent.options.smart_notice_shown and self.parent.options.smart_enabled

    def is_registered(self):
        return self.user is not None and self.user.get("username") is not None

    def is_sync_enabled(self):
        return self.is_smart_enabled() and self.is_registered() and self.parent.options.sync_enabled

    def sync_sources(self, in_thread=False):
        if not self.is_smart_enabled():
            return

        def _run():
            try:
                logger.info("sync: Syncing image sources")

                try:
                    self.load_user(create_if_missing=True)
                except:
                    logger.exception("sync: Could not load or create smart user")
                    return

                sources = [{'enabled': s[0], 'type': Options.type_to_str(s[1]), 'location': s[2]}
                           for s in self.parent.options.sources if s[1] in Options.SourceType.dl_types]

                data = {'sources': sources,  'machine_type': Util.get_os_name()}

                if "machine_id" in self.user:
                    data["machine_id"] = self.user["machine_id"]

                try:
                    sync_url = '%s/user/%s/sync-sources?authkey=%s' % (Smart.API_URL, self.user["id"], self.user["authkey"])
                    server_data = AttrDict(Util.fetch_json(sync_url, {'data': json.dumps(data)}))
                    self.user["machine_id"] = server_data["machine_id"]
                    self.user["machine_label"] = server_data["machine_label"]
                    self.save_user()
                except HTTPError, e:
                    self.handle_user_http_error(e)
                    raise

            except:
                logger.exception("smart: Could not sync sources")

        if in_thread:
            sync_sources_thread = threading.Thread(target=_run)
            sync_sources_thread.daemon = True
            sync_sources_thread.start()
        else:
            _run()

    def _reset_sync(self):
        self.sync_hash = Util.random_hash()  #  stop current sync if running
        self.last_synced = 0

    def sync(self):
        if not self.is_smart_enabled():
            return

        self._reset_sync()
        current_sync_hash = self.sync_hash

        def _run():
            logger.info('sync: Started, hash %s' % current_sync_hash)

            try:
                self.load_user(create_if_missing=True)
            except:
                logger.exception("sync: Could not load or create smart user")
                return

            self.sync_sources(in_thread=False)

            try:
                logger.info("sync: Fetching serverside data")
                try:
                    sync_url = '%s/user/%s/sync?authkey=%s' % (Smart.API_URL, self.user["id"], self.user["authkey"])
                    server_data = AttrDict(Util.fetch_json(sync_url))
                    throttle_interval = int(server_data.throttle_interval) if server_data.throttle_interval else 1
                except HTTPError, e:
                    self.handle_user_http_error(e)
                    raise

                syncdb = self.load_syncdb()

                # First upload local favorites that need uploading:
                logger.info("sync: Uploading local favorites to server")

                files = os.listdir(self.parent.options.favorites_folder)
                files = [os.path.join(self.parent.options.favorites_folder, f) for f in files]
                files = filter(lambda f: os.path.isfile(f) and Util.is_image(f), files)
                files.sort(key=os.path.getmtime)

                for path in files:
                    try:
                        if not self.is_smart_enabled() or current_sync_hash != self.sync_hash:
                            return

                        name = os.path.basename(path)

                        if path in syncdb.local:
                            info = syncdb.local[path]
                        else:
                            info = {}
                            meta = Util.read_metadata(path)
                            source_url = Smart.fix_origin_url(None if meta is None else meta.get("sourceURL", None))
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

                        if imageid in server_data["ignore"]:
                            logger.warning('sync: Skipping upload of %s as it is has been deleted from your profile. '
                                           'To undo this visit: %s' % (name, Smart.SITE_URL + '/image/' + imageid))
                            continue

                        if not imageid in server_data["favorite"]:
                            logger.info("sync: Smart-reporting existing favorite %s" % path)
                            self.report_file(path, "favorite", async=False)
                            time.sleep(throttle_interval)
                        elif "upload_full_image" in server_data["favorite"][imageid]:
                            logger.info("sync: Uploading full image for existing favorite %s" % path)
                            self.report_file(path, "favorite", async=False, upload_full_image=True)
                            time.sleep(throttle_interval)
                        elif "needs_reupload" in server_data["favorite"][imageid]:
                            logger.info("sync: Server requested reupload of existing favorite %s" % path)
                            self.report_file(path, "favorite", async=False, needs_reupload=True)
                            time.sleep(throttle_interval)

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
                        time.sleep(throttle_interval)

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
                            time.sleep(throttle_interval)

                    # Download locally-missing favorites from the server
                    to_sync = []
                    for imageid in server_data["favorite"]:
                        if imageid in server_data["ignore"]:
                            logger.warning('sync: Skipping download of %s as it is has been deleted from your profile. '
                                           'To undo this visit: %s' % (imageid, Smart.SITE_URL + '/image/' + imageid))
                            continue

                        if imageid in server_data["trash"]:
                             # do not download favorites that have later been trashed
                            logger.info('sync: Skipping download of %s as it is also in trash. ' % imageid)
                            continue

                        if imageid in syncdb.remote:
                            if 'success' in syncdb.remote[imageid]:
                                continue  # we have this image locally
                            if syncdb.remote[imageid].get('error', 0) >= 3:
                                continue  # we have tried and got error for this image 3 or more times, leave it alone
                        to_sync.append(imageid)

                    if to_sync:
                        self.parent.show_notification(
                            _("Sync"),
                            (_("Fetching %d images") % len(to_sync)) if len(to_sync) != 1 else _("Fetching 1 image"))

                    for imageid in to_sync:
                        if not self.is_sync_enabled() or current_sync_hash != self.sync_hash:
                            return

                        try:
                            logger.info("sync: Downloading locally-missing favorite image %s" % imageid)
                            image_data = Util.fetch_json(Smart.API_URL + '/image/' + imageid)

                            prefer_source_id = server_data["favorite"][imageid].get("source", None)
                            source = image_data.get("sources", {}).get(prefer_source_id, None)

                            image_url, origin_url, source_type, source_location, source_name, extra_metadata = \
                                Smart.extract_fetch_data(image_data)

                            path = ImageFetcher.fetch(image_url, self.parent.options.favorites_folder,
                                               origin_url=origin_url,
                                               source_type=source[0] if source else source_type,
                                               source_location=source[1] if source else source_location,
                                               source_name=source[2] if source else source_name,
                                               extra_metadata=extra_metadata,
                                               verbose=False)
                            if not path:
                                raise Exception("Fetch failed")

                            self.parent.register_downloaded_file(path)

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
                            time.sleep(throttle_interval)

                    if to_sync:
                        self.parent.show_notification(_("Sync"), _("Finished"))

                self.last_synced = time.time()
            except:
                logger.exception('sync: Error')
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

    def process_login_request(self, userid, username, authkey):
        def _do_login():
            self.parent.show_notification(_('Logged in as %s') % username)
            self.set_user({'id': userid, 'authkey': authkey, 'username': username})
            self.parent.preferences_dialog.close_login_register_dialog()
            if hasattr(self, "register_dialog") and self.register_dialog:
                def _close():
                    self.register_dialog.result = 'logged'
                    self.register_dialog.response(Gtk.ResponseType.OK)
                GObject.idle_add(_close)

        if self.user is None or self.user['authkey'] != authkey:
            def _go():
                dialog = Gtk.MessageDialog(self.parent.preferences_dialog, Gtk.DialogFlags.MODAL, Gtk.MessageType.QUESTION, Gtk.ButtonsType.OK_CANCEL)
                dialog.set_markup(_('Do you want to login to VRTY.ORG as <span font_weight="bold">%s</span>?') % username)
                dialog.set_title(_('VRTY.ORG login confirmation'))
                dialog.set_default_response(Gtk.ResponseType.OK)
                response = dialog.run()
                dialog.destroy()
                if response == Gtk.ResponseType.OK:
                    _do_login()
            Util.add_mainloop_task(_go)

        else:
            _do_login()

    @staticmethod
    def extract_fetch_data(json_image_data):
        image = AttrDict(json_image_data)
        origin_url = image.origin_url
        image_url, source_type, source_location, source_name, extra_metadata = None, None, None, None, {}

        if image.download_url:
            image_url = image.download_url

        if image.sources:
            source = image.sources.values()[0]
            source_type = source[0]
            source_location = source[1]
            source_name = image.origin_name or source[2]

        if image.author and image.author_url:
            extra_metadata['author'] = image.author
            extra_metadata['authorURL'] = image.author_url

        if image.keywords and isinstance(image.keywords, list):
            extra_metadata['keywords'] = image.keywords
        if image.headline:
            extra_metadata['headline'] = image.headline
        if image.description:
            extra_metadata['description'] = image.description
        if "sfw_rating" in image and image.sfw_rating is not None:
            extra_metadata['sfwRating'] = image.sfw_rating

        return image_url, origin_url, source_type, source_location, source_name, extra_metadata