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

from .IVarietyPlugin import IVarietyPlugin


class IQuoteSource(IVarietyPlugin):
    def supports_search(self):
        """
        False means that this plugins does not support searching by keyword or author (only get_random will
        ever be called) and this plugin will be used only if the user has not specified search criteria.
        True means get_for_keyword and get_for_author should also be implemented.
        :return: True or False
        """
        return False

    def get_random(self):
        """
        Returns some quotes.
        Individual quotes are hashes like the one below. Only quote should be non-null, the others can be None.
        """
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
