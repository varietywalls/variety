#!/usr/bin/env python
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

###################### DO NOT TOUCH THIS (HEAD TO THE SECOND PART) ######################

import os
import sys
import glob

try:
    import DistUtilsExtra.auto
except ImportError:
    print('To build variety you need https://launchpad.net/python-distutils-extra', file=sys.stderr)
    sys.exit(1)
assert DistUtilsExtra.auto.__version__ >= '2.18', 'needs DistUtilsExtra.auto >= 2.18'

def update_config(values = {}):

    oldvalues = {}
    try:
        fin = file('variety_lib/varietyconfig.py', 'r')
        fout = file(fin.name + '.new', 'w')

        for line in fin:
            fields = line.split(' = ') # Separate variable from value
            if fields[0] in values:
                oldvalues[fields[0]] = fields[1].strip()
                line = "%s = %s\n" % (fields[0], values[fields[0]])
            fout.write(line)

        fout.flush()
        fout.close()
        fin.close()
        os.rename(fout.name, fin.name)
    except (OSError, IOError) as e:
        print ("ERROR: Can't find variety_lib/varietyconfig.py")
        sys.exit(1)
    return oldvalues


class InstallAndUpdateDataDirectory(DistUtilsExtra.auto.install_auto):
    def run(self):
        values = {'__variety_data_directory__': "'%s'" % (self.prefix + '/share/variety/'),
                  '__version__': "'%s'" % self.distribution.get_version()}
        previous_values = update_config(values)
        DistUtilsExtra.auto.install_auto.run(self)
        update_config(previous_values)

from variety_lib.varietyconfig import get_version

##################################################################################
###################### YOU SHOULD MODIFY ONLY WHAT IS BELOW ######################
##################################################################################

DistUtilsExtra.auto.setup(
    name='variety',
    version=get_version(),
    license='GPL-3',
    author='Peter Levi',
    author_email='peterlevi@peterlevi.com',
    description='Wallpaper changer, downloader and manager',
    long_description=
"Variety changes the desktop wallpaper regularly, using local "
"or automatically downloaded images. "
""
"Variety sits conveniently as an indicator in the panel and can be easily paused "
"and resumed. The mouse wheel can be used to scroll wallpapers back and forth"
""
"Variety can fetch wallpapers from Flickr, Wallhaven.cc, "
"NASA Astronomy Picture of the Day, Desktoppr.co. Media RSS feeds from Picasa, "
"deviantART or any other place are also supported.",
    url='https://launchpad.net/variety',
    cmdclass={'install': InstallAndUpdateDataDirectory},
    data_files=[('share/metainfo', ['variety.appdata.xml'])]
)
