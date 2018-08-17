# Variety

Variety is a wallpaper manager for Linux systems. It supports numerous desktops
and wallpaper sources, including local files and online services: Flickr,
Wallhaven, Unsplash, and more.

Where supported, Variety sits as a tray icon to allow easy pausing and resuming.
Otherwise, its desktop entry menu provides a similar set of options.

Variety also includes a range of image effects, such as oil painting and blur,
as well as options to layer quotes and a clock onto the background.

## Requirements
- Python 3.5+
- GObject introspection / GIRepository bindings for:
    - GDK Pixbuf (Debian/Ubuntu: [gir1.2-gdkpixbuf-2.0](https://packages.debian.org/sid/gir1.2-gdkpixbuf-2.0))
    - gexiv2 (Debian/Ubuntu: [gir1.2-gexiv2-0.10](https://packages.debian.org/sid/gir1.2-gexiv2-0.10))
    - GLib, GObject, GModule, Gio (Debian/Ubuntu: [gir1.2-glib-2.0](https://packages.debian.org/sid/gir1.2-glib-2.0))
    - GTK+ 3 (Debian/Ubuntu: [gir1.2-gtk-3.0](https://packages.debian.org/sid/gir1.2-gtk-3.0))
    - libnotify (Debian/Ubuntu: [gir1.2-gtk-3.0](https://packages.debian.org/sid/gir1.2-gtk-3.0))
    - Pango (Debian/Ubuntu: [gir1.2-pango-1.0](https://packages.debian.org/sid/gir1.2-pango-1.0))
- Python 3 libraries:
    - BeautifulSoup4
    - lxml
    - Cairo bindings for Python 3 (e.g. Debian/Ubuntu [python3-cairo](https://packages.debian.org/sid/python3-cairo))
    - Cairo PyGObject integration (e.g. Debian/Ubuntu [python3-gi-cairo](https://packages.debian.org/sid/python3-gi-cairo))
    - ConfigObj
    - Pillow
    - pkg_resources (from setuptools)
    - Requests
    - *Optional*: httplib2 (for more quotes sources)
- *Optional*: imagemagick (for wallpaper filters)
- *Optional*: feh and/or nitrogen: used by default for wallpaper changing on i3, openbox, and dwm

See `debian/control` for an equivalent list of runtime dependencies on Debian/Ubuntu.
