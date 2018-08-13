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
#
# FacebookHelper is roughly based upon this work: https://github.com/vrruiz/FacebookAuthBrowser
#
#Copyright (c) 2011, Víctor R. Ruiz <rvr@linotipo.es>
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions
#are met:
#
#1. Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#2. Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#3. Neither the name of the author nor the names of its contributors
#   may be used to endorse or promote products derived from this software
#   without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED ''AS IS'' AND ANY EXPRESS OR IMPLIED
#WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
#MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN
#NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
#INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
#NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
#USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
#THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json
import urllib.parse
import pycurl
import io
import logging
import webbrowser

from variety import _
from variety.Util import Util

logger = logging.getLogger('variety')

AUTH_URL = 'https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=%s&response_type=token&scope=%s'
AUTH_REDIRECT_URL = 'https://vrty.org/facebook-auth?hash=%s'
PUBLISH_URL = "https://graph.facebook.com/me/feed"


class FacebookHelper:
    """
    Open's the user's web browser to the Facebook OAuth setup page.
    This requires the Variety's Application ID and saves the retrieved OAuth token to token_file.
    """

    def __init__(self, parent, token_file, app_key='368780939859975', scope='publish_actions'):
        """Creates the FacebookHelper class capable of opening a Facebook OAuth setup page.
           @param app_key Application key ID (Public).

           @param scope A string list of permissions to ask for. More at
           http://developers.facebook.com/docs/reference/api/permissions/
        """
        self.parent = parent
        self.app_key = app_key
        self.token_file = token_file
        self.scope = scope

        self.load_token()

    def authorize(self, on_success=None, on_failure=None):
        logger.info(lambda: "Authorizing for Facebook")

        self.token = ''
        self.token_expire = ''
        self.on_success = on_success
        self.on_failure = on_failure
        self.hash = Util.random_hash()[:4]

        # Loads the Facebook OAuth page
        auth_url = AUTH_URL % (
            urllib.parse.quote(self.app_key),
            urllib.parse.quote(AUTH_REDIRECT_URL % self.hash),
            urllib.parse.quote(self.scope))

        webbrowser.open(auth_url)

    def on_facebook_auth(self, params):
        try:
            if self.hash != params["hash"][0]:
                return  # user has reloaded an old redirect page, ignore it

            self.token = params['access_token'][0]
            self.token_expire = params['expires_in'][0]  # Should be equal to 0, don't expire

            # Save token to file
            with open(self.token_file, 'w') as token_file:
                token_file.write(self.token)
                token_file.close()

            if self.on_success:
                self.parent.show_notification(_("Authorization successful"), _("Publishing..."))
                self.on_success(self, self.token)
        except Exception:
            logger.exception(lambda: "Facebook auth failed")
            if self.on_failure:
                self.on_failure(self, "authorize", _("Authorization failed"))

    def load_token(self):
        logger.info(lambda: "Loading token from file")
        try:
            with open(self.token_file, 'r') as token_file:
                self.token = token_file.read().strip()
        except Exception:
            self.token = None

    def publish(self, message=None, link=None, picture=None, caption=None, description=None,
                on_success=None, on_failure=None, attempts=0):

        message = message.encode('utf8') if type(message) == str else message
        link = link.encode('utf8') if type(link) == str else link

        def republish(action=None, token=None):
            self.publish(message=message, link=link, picture=picture, caption=caption, description=description,
                         on_success=on_success, on_failure=on_failure, attempts=attempts + 1)

        logger.info(lambda: "Publishing to Faceboook, attempt %d" % attempts)
        if not self.token:
            logger.info(lambda: "No auth token, loading from file")
            self.load_token()

        if not self.token:
            logger.info(lambda: "Still no token, trying to authorize")
            self.authorize(on_success=republish, on_failure=on_failure)
            return

        # now we certainly have some token, but it may be expired or invalid
        m = {}
        if message: m["message"] = message
        if link: m["link"] = link
        if picture: m["picture"] = picture
        if caption: m["caption"] = caption
        if description: m["description"] = description

        logger.info(lambda: "Publish properties: " + str(m))

        m["access_token"] = self.token
        try:
            content = FacebookHelper.post(PUBLISH_URL, m)
        except pycurl.error as e:  # pylint: disable=no-member
            on_failure(self, "publish", str(e))
            return

        response = json.loads(content)

        logger.info(lambda: "Response: %s" % content)

        if "error" in response:
            logger.warning(lambda: "Could not publish to Facebook, error message %s" % response["error"]["message"])
            code = response["error"].get("code", -1)
            if attempts < 2 and code in [190, 200]:  # 190 is invalid token, 200 means no permission to publish
                logger.info(lambda: "Code %d, trying to reauthorize" % code)
                self.authorize(on_success=republish, on_failure=on_failure)
                return
            else:
                # Facebook would sometimes return an error on the first try, but succeed on the next,
                # so retry a couple of times
                if attempts < 3:
                    logger.info(lambda: "Retrying to publish")
                    republish()
                else:
                    on_failure(self, "publish", "Facebook message:\n%s" % response["error"]["message"])
        else:
            if on_success:
                on_success(self, "publish", content)

    @staticmethod
    def post(url, post_data, timeout=10):
        # pylint: disable=no-member
        c = pycurl.Curl()
        c.setopt(pycurl.CONNECTTIMEOUT, timeout)
        c.setopt(pycurl.TIMEOUT, timeout)
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.POSTFIELDS, urllib.parse.urlencode(post_data))
        b = io.StringIO()
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.perform()
        c.close()
        return b.getvalue()

