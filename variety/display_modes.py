from variety.Util import Util, _


def _os():
    return None, None


DISPLAY_MODES = [
    {
        "id": "os",
        "title": _("Controlled by OS settings, not by Variety"),
        "description": _(
            "Display mode is controlled by your OS Appearance settings and by what is "
            "specified in set_wallpaper script for your desktop environment. "
        ),
        "fn": _os,
    },
    {
        "id": "zoom",
        "title": _("Zoom"),
        "description": _(
            "Image is zoomed in or out so that it fully fills your primary screen. "
            "Some parts of the image will be cut out if its resolution is different "
            "from the screen's. "
        ),
        "fn": _os,
    },
    {
        "id": "fill-with-black",
        "title": _("Fill with black"),
        "description": _(
            "Image is zoomed in or out so that it fully fits within your primary screen. "
            "The rest of the screen is filled with black. "
        ),
        "fn": _os,
    },
    {
        "id": "fill-with-blur",
        "title": _("Fill with blur"),
        "description": _(
            "Image is zoomed in or out so that it fully fits within your primary screen. "
            "The rest of the screen is a filled with blurred version of the image. "
        ),
        "fn": _os,
    },
    {
        "id": "smart-with-black",
        "title": _("Pick dynamically between Zoom and Fill with black"),
        "description": _(
            "Variety picks a good mode depending on image size. "
            "Images that are close to the screen proportions use 'Zoom'. "
            "Those that are vastly different use 'Fill with black'. "
        ),
        "fn": _os,
    },
    {
        "id": "smart-with-blur",
        "title": _("Pick dynamically between Zoom and Fill with blur"),
        "description": _(
            "Variety picks a good mode depending on image size. "
            "Images that are close to the screen proportions use 'Zoom'. "
            "Those that are vastly different use 'Fill with blur'. "
        ),
        "fn": _os,
    },
]
