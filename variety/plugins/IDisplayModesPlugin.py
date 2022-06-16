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
import abc
from typing import Callable, List, Optional

from variety.Util import Util

from .IVarietyPlugin import IVarietyPlugin


class DisplayModeData:
    """
    Contains the data for how to visualize a specific image.
    set_wallpaper_param - what do we send to the set_wallpaper script, affects OS background options
    imagemagick_cmd - optional, what command do we run over the image in order to resize it
    fixed_image_path - optional, if more complex logic needed, generate the image and give its path
    """

    def __init__(
        self,
        set_wallpaper_param: str,
        imagemagick_cmd: Optional[str] = None,
        fixed_image_path: Optional[str] = None,
    ):
        self.set_wallpaper_param = set_wallpaper_param
        self.imagemagick_cmd = imagemagick_cmd
        self.fixed_image_path = fixed_image_path


class DisplayMode:
    """
    Implements a display mode.
    Needs a unique id, title to show in the combobox, description to show below the combo when
    selected, and callable that implements the logic.
    The callable takes a file path and returns a DisplayModeData object.
    """

    def __init__(self, id: str, title: str, description: str, fn: Callable[[str], DisplayModeData]):
        self.id = id
        self.title = title
        self.description = description
        self.fn = fn


class StaticDisplayMode(DisplayMode):
    """
    A DisplayMode that does not care about the specific file, but implements a uses
    either a static ImageMagick command, or does no resizing at all and works simply via the
    set_wallpaper parameter.
    """

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        set_wallpaper_param: str,
        imagemagick_cmd: Optional[str] = None,
    ):
        def fn(filename: str):
            w, h = Util.get_primary_display_size()
            if imagemagick_cmd:
                final_cmd = imagemagick_cmd.replace("%W", str(w)).replace("%H", str(h))
            else:
                final_cmd = None
            return DisplayModeData(
                set_wallpaper_param=set_wallpaper_param, imagemagick_cmd=final_cmd
            )

        super().__init__(id, title, description, fn)


class IDisplayModesPlugin(IVarietyPlugin):
    @abc.abstractmethod
    def display_modes(self) -> List[DisplayMode]:
        """
        Return a list of DisplayModes
        """
        return []

    def order(self):
        """
        Display modes from IDisplayModesPlugins with lower order get listed before those with
        higher order
        """
        return 100
