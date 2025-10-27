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

__all__ = ["project_path_not_found", "get_data_file", "get_data_path"]
__license__ = "GPL-3"
__version__ = "0.8.13"

import os
import site
import sys
import sysconfig
from pathlib import Path

_DEFAULT_RELATIVE_DATA_DIRECTORY = Path(__file__).resolve().parent / ".." / "data"
_ENV_DATA_PATH = "VARIETY_DATA_PATH"

class project_path_not_found(Exception):
    """Raised when we can't find the project directory."""


def get_data_file(*path_segments):
    """Get the full path to a data file.

    Returns the path to a file underneath the data directory (as defined by
    `get_data_path`). Equivalent to os.path.join(get_data_path(),
    *path_segments).
    """
    return os.path.join(get_data_path(), *path_segments)


def get_data_path():
    """Retrieve variety data path

    Attempts to resolve the data directory from a number of common installation
    locations, preferring:

    1. A custom path specified via the VARIETY_DATA_PATH environment variable
    2. The repository-relative ../data directory (development mode)
    3. Standard share/variety locations under the active Python prefixes
    4. The user's per-account data directory (XDG)
    """

    for candidate in _iter_candidate_data_paths():
        if candidate.is_dir():
            return str(candidate)

    raise project_path_not_found


def _iter_candidate_data_paths():
    env_override = os.environ.get(_ENV_DATA_PATH)
    if env_override:
        yield Path(env_override).expanduser()

    yield _DEFAULT_RELATIVE_DATA_DIRECTORY.resolve()

    prefixes = {
        Path(sys.prefix),
        Path(getattr(sys, "base_prefix", sys.prefix)),
        Path(getattr(sys, "exec_prefix", sys.prefix)),
    }

    try:
        prefixes.add(Path(sysconfig.get_path("data")))
    except (KeyError, TypeError, ValueError):
        pass

    try:
        prefixes.add(Path(site.getuserbase()))
    except (AttributeError, OSError, ValueError):
        pass

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        prefixes.add(Path(xdg_data_home))

    for prefix in prefixes:
        if not prefix:
            continue
        yield (Path(prefix) / "share" / "variety").resolve()


def get_version():
    return __version__
