from typing import List

from variety.plugins.IDisplayModesPlugin import (
    DisplayMode,
    DisplayModeData,
    IDisplayModesPlugin,
    StaticDisplayMode,
)
from variety.Util import Util, _

IMAGEMAGICK_ZOOM = "-scale %Wx%H^ "
IMAGEMAGICK_FIT_WITH_BLACK = "-resize %Wx%H -size %Wx%H xc:black +swap -gravity center -composite"
IMAGEMAGICK_FIT_WITH_BLUR = (
    "-resize %Wx%H^ -gravity center -extent %Wx%H -scale 10% -blur 0x3 -resize 1000% -clone 0 "
    "-resize %Wx%H -size %Wx%H -gravity center -composite"
)
IMAGEMAGICK_TILE = "-write mpr:x -delete -1 -size %Wx%H tile:mpr:x "

def _smart_fn(filename):
    try:
        image_w, image_h = Util.get_size(filename)
        primary_w, primary_h = Util.get_primary_display_size(hidpi_scaled=True)
        total_w, total_h = Util.get_multimonitor_display_size()
        if image_w * image_h * 10 < primary_w * primary_h:
            # image way smaller than primary monitor, tile it
            cmd = IMAGEMAGICK_TILE.replace("%W", str(primary_w)).replace(
                    "%H", str(primary_h)
            )
            return DisplayModeData(set_wallpaper_param="zoom", imagemagick_cmd=cmd)
        else:
            image_ratio = image_w / image_h
            primary_ratio = primary_w / primary_h
            total_ratio = total_w / total_h
            if 2 * abs(image_ratio - primary_ratio) / (image_ratio + primary_ratio) < 0.2:
                # image ratio is close to primary screen ratio, zoom
                return DisplayModeData(set_wallpaper_param="zoom")
            elif 2 * abs(image_ratio - total_ratio) / (image_ratio + total_ratio) < 0.2:
                # image ratio is close to multimonitor total screen ratio, span it
                return DisplayModeData(set_wallpaper_param="spanned")
            else:
                # image ratio not close to screen ratio, fit with a blurred background
                cmd = IMAGEMAGICK_FIT_WITH_BLUR.replace("%W", str(primary_w)).replace(
                    "%H", str(primary_h)
                )
                return DisplayModeData(set_wallpaper_param="zoom", imagemagick_cmd=cmd)
    except:
        return DisplayModeData(set_wallpaper_param="zoom")


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
            DisplayMode(
                id="smart",
                title=_("Smart: Variety picks best mode based on image size. Recommended."),
                description=(
                    "Variety uses the fast OS-provided Zoom mode for images that are close to "
                    "screen proportions, uses 'Fit & pad with a blurred background' when the image "
                    "proportions are significantly different - e.g. portraits on a horizontal "
                    "screen, and uses a screen-covering tiling of the image if it is very small such that it would "
                    "look bad resized."
                ),
                fn=_smart_fn,
            ),
            StaticDisplayMode(
                id="zoom",
                title=_("Zoom to fill screen"),
                description=_(
                    "Image is zoomed in or out so that it fully fills your primary screen. "
                    "Some parts of the image will be cut out if its resolution is different "
                    "from the screen's. Slower than using native OS resizing options."
                ),
                set_wallpaper_param="zoom",
                imagemagick_cmd=IMAGEMAGICK_ZOOM,
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
                imagemagick_cmd=IMAGEMAGICK_FIT_WITH_BLACK,
            ),
            StaticDisplayMode(
                id="fill-with-blur",
                title=_("Fit within screen, pad with a blurred background. Slower."),
                description=_(
                    "Image is zoomed in or out so that it fully fits within your primary screen. "
                    "The rest of the screen is a filled with blurred version of the image. "
                ),
                set_wallpaper_param="zoom",
                imagemagick_cmd=IMAGEMAGICK_FIT_WITH_BLUR,
            ),
        ]

    def order(self):
        return 2000
