from typing import List

from variety.plugins.IDisplayModesPlugin import DisplayMode, IDisplayModesPlugin, StaticDisplayMode
from variety.Util import _


class GnomeDisplayModesPlugin(IDisplayModesPlugin):
    @classmethod
    def get_info(cls):
        return {
            "name": "GnomeDisplayModesPlugin",
            "description": "Display modes relying on the underlying desktop environment",
            "version": "1.0",
            "author": "Peter Levi",
        }

    def display_modes(self) -> List[DisplayMode]:
        modes = ["centered", "scaled", "stretched", "zoom", "spanned", "wallpaper"]
        return [
            StaticDisplayMode(
                id="gnome-%s" % mode,
                title=_("[GNOME/Mate/Cinnamon] %s") % mode.capitalize(),
                description=_(
                    "Variety will instruct the desktop environment to use this mode when "
                    "calling set_wallpaper, and will not itself scale the image, unless needed "
                    "by other options, e.g. clock. "
                ),
                set_wallpaper_param=mode,
            )
            for mode in modes
        ]

    def order(self):
        return 3000
