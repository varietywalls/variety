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

from variety import _

FILTERS = {
    "Keep original": _("Keep original"),
    "Grayscale": _("Grayscale"),
    "Heavy blur": _("Heavy blur"),
    "Soft blur": _("Soft blur"),
    "Oil painting": _("Oil painting"),
    "Pencil sketch": _("Pencil sketch"),
    "Pointilism": _("Pointilism"),
    "Pixellate": _("Pixellate"),
}

SOURCES = {
    "favorites": ("The Favorites folder", _("The Favorites folder")),
    "fetched": ("The Fetched folder", _("The Fetched folder")),
    "recommended": (
        "Recommended by Variety. Adapts to your taste as you mark images as favorite or trash.",
        _("Recommended by Variety. Adapts to your taste as you mark images as favorite or trash."),
    ),
    "latest": (
        "Latest favorites by the other users of Variety. [May contain NSFW images]",
        _("Latest favorites by the other users of Variety. [May contain NSFW images]"),
    ),
    "desktoppr": ("Random wallpapers from Desktoppr.co", _("Random wallpapers from Desktoppr.co")),
    "apod": ("NASA's Astronomy Picture of the Day", _("NASA's Astronomy Picture of the Day")),
    "earth": (
        "World Sunlight Map - live wallpaper from Die.net",
        _("World Sunlight Map - live wallpaper from Die.net"),
    ),
    "bing": ("Bing Photo of the Day", _("Bing Photo of the Day")),
    "unsplash": (
        "High-resolution photos from Unsplash.com",
        _("High-resolution photos from Unsplash.com"),
    ),
}

TIPS = [
    _(
        "You can change the wallpaper back and forth by scrolling the mouse wheel on top of the indicator icon."
    ),
    _(
        "If you want to run custom commands every time the wallpaper changes or if you use an alternative desktop environment, please edit the scripts in ~/.config/variety/scripts. There are examples there for various desktop environments."
    ),
    _(
        'Variety can be controlled from the command line and you can use this to define keyboard shortcuts for the operations you use most often. Run "variety --help" to see all available commands.'
    ),
    _(
        'You can drop image links or files on the launcher icon to download them and use them as wallpapers. For quicker downloading from a specific site, you can also use clipboard monitoring (see "Manual downloading" tab).'
    ),
    _(
        "Applying a heavy blurring filter is a great way to get abstract-looking and unobtrusive, yet colorful wallpapers, similar in spirit to the default one in Ubuntu."
    ),
    _(
        "Adding your own custom filters is quite easy: open ~/.config/variety/variety.conf in an editor and use the existing filters as an example. Every filter is just a line of options to be passed to ImageMagick's convert command."
    ),
    _(
        'When you select an image source, its images are displayed in a window at the bottom of the screen. Click an image there to set is as wallpaper. Right-click to close the window, to modify its appearance or to perform file operations. You can select multiple image sources to create a "merged" thumbnail view of all of them. Please mind that thumbnail view is limited to several hundred randomly selected images.'
    ),
    _(
        "To enable desktop notifications when the wallpaper changes, uncomment the two lines at the bottom of ~/.config/variety/scripts/set_wallpaper."
    ),
    _(
        'Variety\'s indicator icon is themeable - if you you choose the "Light" option for the icon, Variety will first check if the current GTK theme has an icon named "variety-indicator" and will use it instead of the bundled light icon.'
    ),
    _(
        "When you choose to save quotes to Favorites, these are by default saved to ~/.config/variety/favorite_quotes.txt. This file is compatible with Variety's local files quote source. If you want to use it - copy it to ~/.config/variety/pluginconfig/quotes/ and enable the Local Files quote source. This file is also compatible with the Unix fortune utility."
    ),
]
