# Variety

Variety is a wallpaper manager for Linux systems. It supports numerous desktops
and wallpaper sources, including local files and online services: Flickr,
Wallhaven, Unsplash, and more.

Where supported, Variety sits as a tray icon to allow easy pausing and resuming.
Otherwise, its desktop entry menu provides a similar set of options.

Variety also includes a range of image effects, such as oil painting and blur,
as well as options to layer quotes and a clock onto the background.

## Installation

### As a system package

Variety is available in the distro repositories of:

- [Arch Linux](https://www.archlinux.org/packages/community/any/variety/)
- [Debian 9+](https://packages.debian.org/search?keywords=variety)
- [Fedora](https://www.rpmfind.net/linux/rpm2html/search.php?query=variety)
- [OpenSUSE](https://software.opensuse.org/package/variety?search_term=variety)
- [Ubuntu 16.04+](https://packages.ubuntu.com/search?keywords=variety)

### Ubuntu PPA
Variety backports to older Ubuntu releases are available at https://launchpad.net/~variety/+archive/ubuntu/stable (a NEW location as of April 2019).

### Install from source
To install Variety from source, you will need Git, Python 3.5+ and [distutils-extra](https://launchpad.net/python-distutils-extra). To actually run Variety, you will also need the following:

#### Runtime Requirements
- GTK+ 3
- gexiv2
- libnotify
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
- *Optional*: feh or nitrogen: used by default to set wallpapers on i3, openbox, and other WMs

See `debian/control` for an equivalent list of runtime dependencies on Debian/Ubuntu.

#### Install steps

1. Clone the git repository: `git clone https://github.com/varietywalls/variety.git && cd variety`

2. Run `python3 setup.py install`. By default, this will install Variety into `/usr/local`; for a local installation, use `python3 setup.py install --prefix $HOME/.local`.

3. Run `variety` from the command line or its desktop menu entry!
