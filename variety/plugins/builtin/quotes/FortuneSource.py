# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (c) 2019, Dan Jones
# Copyright (c) 2019, Peter Levi <peterlevi@peterlevi.com>
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
# Based on gist: https://gist.github.com/goodevilgenius/3878ce0f3e232e3daf5c
#

import subprocess
from locale import gettext as _

from variety.plugins.IQuoteSource import IQuoteSource


class FortuneSource(IQuoteSource):
    @classmethod
    def get_info(cls):
        return {
            "name": "UNIX fortune program",
            "description": _(
                "Displays quotes using the UNIX fortune program. "
                "You may want to install additional fortune packs, e.g. fortunes-bofh-excuses."
            ),
            "author": "Dan Jones",
            "version": "0.1",
        }

    def get_random(self):
        fortune = subprocess.check_output(["fortune"]).decode().strip()
        q = fortune.split("--")
        quote = q[0].strip()
        author = q[1].strip() if len(q) > 1 else None
        return [
            {"quote": quote, "author": author, "sourceName": "UNIX fortune program", "link": None}
        ]
