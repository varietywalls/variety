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

import StringIO
import os
import platform
import time
from variety.Options import Options
from gi.repository import Gdk
from variety_lib import varietyconfig

class Stats:

    @staticmethod
    def get_stats(parent):
        # start with user's options:
        options = Options()
        options.read()

        # remove all references to local folders and files:
        options.favorites_folder = ""
        options.download_folder = ""
        options.fetched_folder = ""
        options.sources = [s for s in options.sources if s[1] not in (Options.SourceType.FOLDER, Options.SourceType.IMAGE)]
        options.favorites_operations = [
            ("custom_folder" if place not in ["/", "Downloaded", "Fetched", "Others"] else place, op)
            for (place, op) in options.favorites_operations]

        # add some general OS and desktop environment information
        options.config["platform"] = str(platform.platform())
        options.config["linux_distribution"] = str(platform.linux_distribution())
        options.config["desktop_session"] = str(os.getenv('DESKTOP_SESSION'))

        # add screen info - resolution, monitor count, etc.
        options.config["screen_width"] = str(Gdk.Screen.get_default().get_width())
        options.config["screen_height"] = str(Gdk.Screen.get_default().get_height())
        options.config["monitor_count"] = str(Gdk.Screen.get_default().get_n_monitors())

        # add some other Variety-specifics things:
        options.config["variety_version"] = varietyconfig.get_version()
        options.config["image_count"] = parent.image_count
        with open(os.path.join(parent.config_folder, ".firstrun"), 'r') as f:
            options.config["first_run_timestamp"] = f.read()

        # add a timestamp
        options.config["report_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        # strip comments:
        for k in options.config.comments.keys():
            options.config.comments[k] = []
        options.config.initial_comment = ""
        options.config.final_comment = ""

        s = StringIO.StringIO()
        options.write(reread_first=False, outfile=s)
        result = s.getvalue()
        s.close()

        return result

