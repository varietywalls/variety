# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (c) 2012, Peter Levi <peterlevi@peterlevi.com>
# Copyright (c) 2025, James Lu <james@overdrivenetworks.com>
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

__all__ = ["get_data_file"]

__license__ = "GPL-3"
__version__ = "0.9.0a1"

import importlib.resources

def get_data_file(*path_segments):
    """Get the full path to a data file."""

    pkg_files_root = importlib.resources.files('variety') / 'data'
    return str(pkg_files_root.joinpath(*path_segments))

def get_version():
    return __version__