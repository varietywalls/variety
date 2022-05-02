from typing import List

from variety.plugins.IDisplayModesPlugin import DisplayMode, IDisplayModesPlugin, StaticDisplayMode
from variety.Util import _


class LegacyDisplayModesPlugin(IDisplayModesPlugin):
    @classmethod
    def get_info(cls):
        return {
            "name": "LegacyDisplayModesPlugin",
            "description": "Legacy display mode for compatibility with past Variety versions",
            "version": "1.0",
            "author": "Peter Levi",
        }

    def display_modes(self) -> List[DisplayMode]:
        return [
            StaticDisplayMode(
                id="os",
                title=_("[Legacy] Controlled via OS settings, not by Variety. Fast."),
                description=_(
                    "Display mode is controlled by your OS Appearance settings and by what is "
                    "specified in set_wallpaper script for your desktop environment. "
                    "Provides compatibility with past Variety versions."
                ),
                set_wallpaper_param="os",
            )
        ]

    def order(self):
        return -1000
