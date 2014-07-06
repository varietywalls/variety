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

from gi.repository import Gtk, Gdk, WebKit
import json
import urllib
import urlparse
import pycurl
import StringIO
import logging

from variety import _, _u

logger = logging.getLogger('variety')

AUTH_URL = 'https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=%s&response_type=token&scope=%s'
PUBLISH_URL = "https://graph.facebook.com/me/feed"

class FacebookHelper:
    """ Creates a web browser using GTK+ and WebKit to authorize a
        desktop application in Facebook. It uses OAuth 2.0.
        Requires the Facebook's Application ID. The token is then
        saved to token_file.
    """

    def __init__(self, token_file, app_key='368780939859975', scope='publish_stream'):
        """ Constructor. Creates the GTK+ app and adds the WebKit widget
            @param app_key Application key ID (Public).

            @param scope A string list of permissions to ask for. More at
            http://developers.facebook.com/docs/reference/api/permissions/
        """
        self.app_key = app_key
        self.token_file = token_file
        self.scope = scope

        self.load_token()

    def authorize(self, on_success=None, on_failure=None):
        logger.info("Authorizing for Facebook")

        self.token = ''
        self.token_expire = ''

        # Creates the GTK+ app
        self.window = Gtk.Window()
        self.window.set_title(_("Variety - Login to Facebook"))
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.scrolled_window = Gtk.ScrolledWindow()

        # Creates a WebKit view
        self.web_view = WebKit.WebView()
        self.scrolled_window.add(self.web_view)
        self.window.add(self.scrolled_window)

        # Connects events

        def destroy_event_cb(widget, parent=self, on_failure=on_failure):
            parent._destroy_event_cb(widget, on_failure)

        def load_committed_cb(web_view, frame, parent=self, on_success=on_success):
            parent._load_committed_cb(web_view, frame, on_success)

        self.window.connect('destroy', destroy_event_cb) # Close window

        self.web_view.connect('load-committed', load_committed_cb) # Load page

        self.window.set_default_size(1024, 800)
        # Loads the Facebook OAuth page
        self.web_view.load_uri(
            AUTH_URL % (
                urllib.quote(self.app_key),
                urllib.quote('https://www.facebook.com/connect/login_success.html'),
                urllib.quote(self.scope))
            )

    def _load_committed_cb(self, web_view, frame, on_success):
        """ Callback. The page is about to be loaded. This event is captured
            to intercept the OAuth 2.0 redirection, which includes the
            access token.

            @param web_view A reference to the current WebKitWebView.

            @param frame A reference to the main WebKitWebFrame.
        """
        # Gets the current URL to check whether is the one of the redirection
        uri = frame.get_uri()
        parse = urlparse.urlparse(uri)
        if (hasattr(parse, 'netloc') and hasattr(parse, 'path') and
            hasattr(parse, 'fragment') and parse.netloc == 'www.facebook.com' and
            parse.path == '/connect/login_success.html' and parse.fragment):
            # Get token from URL
            params = urlparse.parse_qs(parse.fragment)
            self.token = params['access_token'][0]
            self.token_expire = params['expires_in'][0] # Should be equal to 0, don't expire
            # Save token to file
            with open(self.token_file, 'w') as token_file:
                token_file.write(self.token)
                token_file.close()
            self.window.destroy()
            if on_success:
                on_success(self, self.token)
        else:
            self.window.show_all()

    def _destroy_event_cb(self, widget, on_failure):
        self.window.destroy()
        if not self.token and on_failure:
            on_failure(self, "authorize", _("Login window closed before authorization"))

    def load_token(self):
        logger.info("Loading token from file")
        try:
            with open(self.token_file, 'r') as token_file:
                self.token = token_file.read().strip()
        except Exception:
            self.token = None

    def publish(self, message=None, link=None, picture=None, caption=None, description=None,
                on_success=None, on_failure=None, attempts=0):

        message = message.encode('utf8') if type(message) == unicode else message
        link = link.encode('utf8') if type(link) == unicode else link

        def republish(action=None, token=None):
            self.publish(message=message, link=link, picture=picture, caption=caption, description=description,
                         on_success=on_success, on_failure=on_failure, attempts=attempts + 1)

        logger.info("Publishing to Faceboook, attempt %d" % attempts)
        if not self.token:
            logger.info("No auth token, loading from file")
            self.load_token()

        if not self.token:
            logger.info("Still no token, trying to authorize")
            self.authorize(on_success=republish, on_failure=on_failure)
            return

        # now we certainly have some token, but it may be expired or invalid
        m = {}
        if message: m["message"] = message
        if link: m["link"] = link
        if picture: m["picture"] = picture
        if caption: m["caption"] = caption
        if description: m["description"] = description

        logger.info("Publish properties: " + str(m))

        m["access_token"] = self.token
        try:
            content = FacebookHelper.post(PUBLISH_URL, m)
        except pycurl.error, e:
            on_failure(self, "publish", str(e))
            return

        response = json.loads(content)

        logger.info("Response: %s" % content)

        if "error" in response:
            logger.warning("Could not publish to Facebook, error message %s" % response["error"]["message"])
            code = response["error"].get("code", -1)
            if attempts < 2 and code in [190, 200]: # 190 is invalid token, 200 means no permission to publish
                logger.info("Code %d, trying to reauthorize" % code)
                self.authorize(on_success=republish, on_failure=on_failure)
                return
            else:
                # Facebook would sometimes return an error on the first try, but succeed on the next,
                # so retry a couple of times
                if attempts < 3:
                    logger.info("Retrying to publish")
                    republish()
                else:
                    on_failure(self, "publish", "Facebook message:\n%s" % response["error"]["message"])
        else:
            if on_success:
                on_success(self, "publish", content)

    @staticmethod
    def post(url, post_data, timeout=10):
        c = pycurl.Curl()
        c.setopt(pycurl.CONNECTTIMEOUT, timeout)
        c.setopt(pycurl.TIMEOUT, timeout)
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.POSTFIELDS, urllib.urlencode(post_data))
        b = StringIO.StringIO()
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.perform()
        c.close()
        return b.getvalue()

if __name__ == '__main__':
    def success(browser, token):
        print "Token: %s" % token
        browser.authorize()

    def cancel(browser):
        print "Pity."
        Gtk.main_quit()

    browser = FacebookHelper(app_key='368780939859975', token_file=".fbtoken", scope='publish_stream')
    def on_success(browser, action, data): print "Published"; Gtk.main_quit()
    def on_failure(browser, action, error): print "Pity"; Gtk.main_quit()
    browser.publish(message="Testing something, ignore", link="http://google.com",
                    on_success=on_success,
                    on_failure=on_failure)
    Gtk.main()
