from typing import List

from variety.plugins.IDisplayModesPlugin import DisplayMode, IDisplayModesPlugin, StaticDisplayMode
from variety.Util import _


class ResizingDisplayModesPlugin(IDisplayModesPlugin):
    @classmethod
    def get_info(cls):
        return {
            "name": "ResizingDisplayModesPlugin",
            "description": "Display modes that use image resizing within Variety",
            "version": "1.0",
            "author": "Peter Levi",
        }

    def display_modes(self) -> List[DisplayMode]:
        return [
            StaticDisplayMode(
                id="zoom",
                title=_("Zoom to fill screen"),
                description=_(
                    "Image is zoomed in or out so that it fully fills your primary screen. "
                    "Some parts of the image will be cut out if its resolution is different "
                    "from the screen's. Slower than using native OS resizing options."
                ),
                set_wallpaper_param="zoom",
                imagemagick_cmd="-scale %Wx%H^ ",
            ),
            StaticDisplayMode(
                id="fill-with-black",
                title=_("Fit within screen, pad with black"),
                description=_(
                    "Image is zoomed in or out so that it fully fits within your primary screen. "
                    "The rest of the screen is filled with black. "
                    "Slower than using native OS resizing options."
                ),
                set_wallpaper_param="zoom",
                imagemagick_cmd="-resize %Wx%H -size %Wx%H xc:black +swap -gravity center -composite",
            ),
            StaticDisplayMode(
                id="fill-with-blue",
                title=_("Fit within screen, pad with a blurred background (Slow)"),
                description=_(
                    "Image is zoomed in or out so that it fully fits within your primary screen. "
                    "The rest of the screen is a filled with blurred version of the image. "
                    "This is a slow option, cause blurring is a slow operation."
                ),
                set_wallpaper_param="zoom",
                imagemagick_cmd=(
                    "-resize %Wx%H^ -gravity center -extent %Wx%H -blur 0x7 -clone 0 "
                    "-resize %Wx%H -size %Wx%H -gravity center -composite"
                ),
            ),
        ]

    def order(self):
        return 100
