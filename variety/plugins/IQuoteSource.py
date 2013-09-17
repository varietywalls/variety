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

from IVarietyPlugin import IVarietyPlugin

class IQuoteSource(IVarietyPlugin):
    def supports_search(self):
        return False

    def get_random(self):
        """Returns some quotes"""
        return [{
            "quote": "Quote",
            "author": "Author",
            "sourceName": "My Quote Site",
            "link": "http://example.com"
        }]

    def get_for_keyword(self, keyword):
        """
        Returns some quotes matching the given keyword.
        Returns [] if it cannot find matches.
        """
        return []

    def get_for_author(self, author):
        """
        Returns some quotes matching the given author.
        Returns [] if it cannot find matches.
        """
        return []
