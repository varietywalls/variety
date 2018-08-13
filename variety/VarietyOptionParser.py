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

import optparse
from variety import safe_print


class VarietyOptionParser(optparse.OptionParser):
    """Override optparse.OptionParser to allow for errors in options without exiting"""

    def __init__(self, usage, version, report_errors=True):
        optparse.OptionParser.__init__(self, usage=usage, version=version)
        self.report_errors = report_errors

    def print_help(self, file=None):
        """print_help(file : file = stdout)

        Print an extended help message, listing all options and any
        help text provided with them, to 'file' (default stdout).
        """
        if file is None:
            safe_print(self.format_help())
        else:
            file.write(self.format_help().encode())

    def error(self, msg):
        if self.report_errors:
            optparse.OptionParser.error(self, msg)
        else:
            raise ValueError(msg)
