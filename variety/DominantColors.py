# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Peter Levi <peterlevi@peterlevi.com>
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

from PIL import Image, ImageFilter
import sys

class DominantColors():
    def __init__(self, imageName):
        self.imageName = imageName
        self.pic = Image.open(imageName)
        self.pic = self.pic.resize((50, 50))
        # self.pic = self.pic.filter(ImageFilter.BLUR)

        # load image data
        self.imgData = self.pic.load()

    def get_dominant(self):
        # print ("Calc dom colors for " + self.imageName)
        colors = [(0,0,0),(128, 128, 128), (192, 192, 192), (255, 255, 255), (128, 0, 0), (255, 0, 0), (128, 128, 0), (255, 255, 0),
            (0, 128, 0), (0, 255, 0), (0, 128, 128), (0, 255, 255), (0, 0, 128), (0, 0, 255), (128, 0, 128), (255, 0, 255)]
        total = 0
        pixel_sum = 0

        iterations = 1
        for counter in xrange(iterations): # perform only X iterations of clustering, that should be enough
            sums = {}
            counts = {}

            for c in colors:
                sums[c] = [0, 0, 0]
                counts[c] = 0

            total = 0
            pixel_sum = 0
            for x in xrange(0, self.pic.size[0], 2):
                for y in xrange(0, self.pic.size[1], 2):
                    total += 4
                    pixel = self.imgData[x, y]
                    if not tuple == type(pixel):
                        pixel = (pixel, pixel, pixel)
                    pixel_sum += sum(pixel) / 3
                    color1 = min((DominantColors.diff(c, pixel), c) for c in colors)[1]
                    color2 = min((DominantColors.diff(c, pixel), c) for c in colors if c != color1)[1]
                    for i in [0,1,2]:
                       sums[color1][i] += 3*pixel[i]
                       sums[color2][i] += 1*pixel[i]
                    counts[color1] = counts[color1] + 3
                    counts[color2] = counts[color2] + 1

            colors = [c for c in colors if counts[c] > 0]
            if counter == iterations - 1:
                colors = map(lambda c: (counts[c], (sums[c][0] // counts[c], sums[c][1] // counts[c], sums[c][2] // counts[c])), colors)
            else:
                colors = map(lambda c: (sums[c][0] // counts[c], sums[c][1] // counts[c], sums[c][2] // counts[c]), colors)

        s = sorted(colors, key=lambda x: x[0], reverse=True)
        return total, s, pixel_sum * 4 // total

    @staticmethod
    def contains_color(dominant_colors, color, fuzziness):
        total, colors, _ = dominant_colors
#        colors = [x for x in colors if x[0] > total / (40 + fuzziness * 40)]
        for position, c in enumerate(colors[:3]):
            if DominantColors.diff(c[1], color) < 1000 + (fuzziness * 1000) + max(0, 5 - position) * 300:
                return True
        return False

    @staticmethod
    def close_colors(c1, c2, fuzziness):
        return DominantColors.diff(c1, c2) < 2000 + (fuzziness * 1000)

    @staticmethod
    def diff(c1, c2):
        return sum((c1[i] - c2[i])**2 for i in [0,1,2])
    
if __name__ == '__main__':
    pc = DominantColors(sys.argv[1])
    print pc.get_dominant()

