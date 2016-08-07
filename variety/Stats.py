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
import platform
import time
from variety.Options import Options
from variety.Util import Util
from gi.repository import Gdk
from variety_lib import varietyconfig


class Stats:

    @staticmethod
    def get_sanitized_config(parent):
        options = parent.options
        config = dict(options.__dict__)

        del config['configfile']

        # remove all references to local folders and files:
        config['favorites_folder'] = \
            'Default' if options.favorites_folder == os.path.expanduser(u"~/.config/variety/Favorites") else 'Changed'
        config['download_folder'] = \
            'Default' if options.download_folder == os.path.expanduser(u"~/.config/variety/Downloaded") else 'Changed'
        config['fetched_folder'] = \
            'Default' if options.fetched_folder == os.path.expanduser(u"~/.config/variety/Fetched") else 'Changed'
        config['copyto_folder'] = \
            'Default' if options.copyto_folder == 'Default' else 'Changed'
        config['quotes_favorites_file'] = \
            'Default' if options.quotes_favorites_file == os.path.expanduser(u"~/.config/variety/favorite_quotes.txt") else 'Changed'
        config['slideshow_custom_folder'] = \
            'Default' if options.slideshow_custom_folder == Util.get_xdg_pictures_folder() else 'Changed'

        config['sources'] = [s for s in options.sources if s[1] not in
                             (Options.SourceType.FOLDER, Options.SourceType.IMAGE)]
        config['favorites_operations'] = [
            ("custom_folder" if place not in ["/", "Downloaded", "Fetched", "Others"] else place, op)
            for (place, op) in options.favorites_operations]

        # add some general OS and desktop environment information
        config["platform"] = str(platform.platform())
        distro = platform.linux_distribution()
        config["linux_distribution"] = distro
        config["linux_distribution_distname"] = str(distro[0])
        config["linux_distribution_version"] = str(distro[1])
        config["linux_distribution_id"] = str(distro[2])
        config["desktop_session"] = str(os.getenv('DESKTOP_SESSION'))

        # add screen info - resolution, monitor count, etc.
        config["total_screen_width"] = Gdk.Screen.get_default().get_width()
        config["total_screen_height"] = Gdk.Screen.get_default().get_height()
        config["monitor_count"] = Gdk.Screen.get_default().get_n_monitors()

        try:
            rect = Gdk.Screen.get_default().get_monitor_geometry(Gdk.Screen.get_default().get_primary_monitor())
            config['primary_monitor_width'] = rect.width
            config['primary_monitor_height'] = rect.height
        except:
            pass

        # add some other Variety-specifics things:
        config["variety_version"] = varietyconfig.get_version()
        config["image_count"] = parent.image_count
        with open(os.path.join(parent.config_folder, ".firstrun"), 'r') as f:
            config["first_run_timestamp"] = f.read()

        # add a timestamp
        config["report_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        return config

