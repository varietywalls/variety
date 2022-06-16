from variety.Util import Util, _


def _os(filename):
    return "os", None


def _zoom(filename):
    w, h = Util.get_primary_display_size()
    return "zoom", "-scale %dx%d^ " % (w, h)


def _fill_with_black(filename):
    w, h = Util.get_primary_display_size()
    return (
        "zoom",
        "-resize %dx%d\> -size %dx%d xc:black +swap -gravity center -composite" % (w, h, w, h),
    )


def _fill_with_blur(filename):
    w, h = Util.get_primary_display_size()
    return (
        "zoom",
        "-resize %dx%d^ -gravity center -extent %dx%d -blur 0x10 -clone 0 -resize %dx%d -size %dx%d -gravity center -composite"
        % (w, h, w, h, w, h, w, h),
    )


DISPLAY_MODES = [
    {
        "id": "os",
        "title": _("Controlled by OS settings, not by Variety. Fastest option."),
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
        "fn": _zoom,
    },
    {
        "id": "fill-with-black",
        "title": _("Fill with black"),
        "description": _(
            "Image is zoomed in or out so that it fully fits within your primary screen. "
            "The rest of the screen is filled with black. "
        ),
        "fn": _fill_with_black,
    },
    {
        "id": "fill-with-blur",
        "title": _("Fill with blur. Slow."),
        "description": _(
            "Image is zoomed in or out so that it fully fits within your primary screen. "
            "The rest of the screen is a filled with blurred version of the image. "
        ),
        "fn": _fill_with_blur,
    },
    {
        "id": "smart-with-black",
        "title": _("Pick dynamically between Zoom and Fill with black"),
        "description": _(
            "Variety picks a good mode depending on image size. "
            "Images that are close to the screen proportions use 'Zoom'. "
            "Those that are vastly different use 'Fill with black'. "
        ),
        "fn": _fill_with_black,  # TODO implement
    },
    {
        "id": "smart-with-blur",
        "title": _("Pick dynamically between Zoom and Fill with blur. Slow."),
        "description": _(
            "Variety picks a good mode depending on image size. "
            "Images that are close to the screen proportions use 'Zoom'. "
            "Those that are vastly different use 'Fill with blur'. "
        ),
        "fn": _fill_with_blur,  # TODO implement
    },
]
