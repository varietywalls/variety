#!/usr/bin/python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2012 Peter Levi <peterlevi@peterlevi.com>
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

#   iterate through each pixel in an image and
#   determine the average rgb color

# you will need to install the PIL module

from PIL import Image

class AvgColor(object):
    ''' loop through each pixel and average rgb '''

    def __init__(self, imageName):
        self.pic = Image.open(imageName)
        self.pic = self.pic.resize((20, 20))
        # load image data
        self.imgData = self.pic.load()

    def getAvg(self):
        r, g, b = 0, 0, 0
        count = 0
        for x in xrange(0, self.pic.size[0], 1):
            for y in xrange(0, self.pic.size[1], 1):
                clrs = self.imgData[x, y]
                try:
                    r += clrs[0]
                    g += clrs[1]
                    b += clrs[2]
                    count += 1
                except TypeError:
                    r += clrs
                    g += clrs
                    b += clrs
                    count += 1
        # calculate averages
        return (r / count), (g / count), (b / count)

if __name__ == '__main__':
    # assumes you have a test.jpg in the working directory!
    pc = AvgColor('test.jpg')
    print "(red, green, blue, total_pixel_count)"
    print pc.getAvg()

