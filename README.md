# Variety

Variety is a wallpaper manager for Linux systems. It supports out-of-the-box most Linux desktop environments, and can be configured to work 
on more esoteric ones.

It can use local images or automatically download wallpapers from Flickr, Wallhaven, Unsplash, Bing, Reddit and other online sources, 
allows you to rotate them on a regular interval, and provides easy ways to separate the great images from the junk. 
Variety can also display wise and funny quotations or a nice digital clock on the desktop.

Where supported, Variety sits as a tray icon to allow easy pausing and resuming.
Otherwise, its desktop entry menu provides a similar set of options.

## Screenshot

![Screenshot from 2022-07-30 16-36-55](https://user-images.githubusercontent.com/1457048/181916884-8a388e15-67dc-45ff-a8e2-e05aac7fca91.png)


## Installation

### As a system package

Variety is available in the distro repositories of:

- [Arch Linux](https://archlinux.org/packages/extra/any/variety/)
- [Debian 9+](https://packages.debian.org/search?keywords=variety)
- [Fedora](https://www.rpmfind.net/linux/rpm2html/search.php?query=variety)
- [OpenSUSE](https://software.opensuse.org/package/variety?search_term=variety)
- [Ubuntu 16.04+](https://packages.ubuntu.com/search?keywords=variety)
- [NixOS](https://search.nixos.org/packages?show=variety&type=packages&query=variety)

Detailed installation instructions can be found [here](https://peterlevi.com/variety/how-to-install/).

On a recent Ubuntu or Debian-based system (Universe repository has to be enabled on Ubuntu):
```
sudo apt update && sudo apt install variety
```

### Ubuntu PPA
Variety backports to older Ubuntu releases are available at this PPA: https://launchpad.net/~variety/+archive/ubuntu/stable.
The PPA usually provides newer releases than the ones available in the Universe repository:

```
sudo add-apt-repository ppa:variety/stable
sudo apt update
sudo apt install variety
```

If you have added the PPA, you may also install [Variety Slideshow](https://github.com/peterlevi/variety-slideshow) – a pan and zoom image slideshow/screensaver, which is an nice optional addition and integrates well into Variety. It is not available in the standard Ubuntu Universe repository.

```
sudo apt install variety-slideshow
```

### Install from source
To install Variety from source, you will need Git, Python 3.5+ and [distutils-extra](https://launchpad.net/python-distutils-extra). To actually run Variety, you will also need the following:

#### Runtime Requirements
- GTK+ 3
- gexiv2
- libnotify
- Python 3 libraries:
    - BeautifulSoup4
    - lxml
    - Pycairo
    - PyGObject, built with Cairo integration
    - ConfigObj
    - Pillow
    - pkg_resources (from setuptools)
    - Requests
    - *Optional*: httplib2 (for more quotes sources)
- *Optional*: imagemagick (for wallpaper filters)
- *Optional*: feh or nitrogen: used by default to set wallpapers on i3, openbox, and other WMs
- *Optional*: libayatana-indicator (for AppIndicator support)
- *Optional*: for tray icon support on GNOME, the [GNOME AppIndicator extension](https://github.com/ubuntu/gnome-shell-extension-appindicator)
- *Optional*: libavif-gdk-pixbuf (for avif format support)

See `debian/control` for an equivalent list of runtime dependencies on Debian/Ubuntu.

#### Install steps

1. Clone the git repository: `git clone https://github.com/varietywalls/variety.git && cd variety`

2. Run `python3 setup.py install`. By default, this will install Variety into `/usr/local`; for a local installation, use `python3 setup.py install --prefix $HOME/.local`.

3. Run `variety` from the command line or its desktop menu entry.

## Launching

Regardless of how you install, you can launch Variety from the dash or applications menu, or by running `variety` in a terminal.

Run `variety --help` to see the command-line options. They allow you to control Variety from the terminal.


