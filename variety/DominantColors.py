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

import sys

from PIL import Image, ImageFilter


class DominantColors:
    def __init__(self, image_name, only_size_needed=True):
        self.imageName = image_name
        self.original = Image.open(image_name)

        if not only_size_needed:
            self.resized = self.original.resize((50, 50))
            # self.resized = self.resized.filter(ImageFilter.BLUR)

            # load image data
            self.img_data = self.resized.load()

    def get_width(self):
        return self.original.size[0]

    def get_height(self):
        return self.original.size[1]

    def get_lightness(self):
        count = 0
        pixel_sum = 0
        for x in range(0, self.resized.size[0]):
            for y in range(0, self.resized.size[1]):
                count += 1
                pixel = self.img_data[x, y]
                if not tuple == type(pixel):
                    pixel_sum += pixel
                else:
                    pixel_sum += sum(pixel) / 3
        return pixel_sum // count

    def get_dominant_colors(self):
        colors = [
            (0, 0, 0),
            (128, 128, 128),
            (192, 192, 192),
            (255, 255, 255),
            (128, 0, 0),
            (255, 0, 0),
            (128, 128, 0),
            (255, 255, 0),
            (0, 128, 0),
            (0, 255, 0),
            (0, 128, 128),
            (0, 255, 255),
            (0, 0, 128),
            (0, 0, 255),
            (128, 0, 128),
            (255, 0, 255),
        ]
        total = 0
        pixel_sum = 0

        iterations = 1
        for counter in range(
            iterations
        ):  # perform only X iterations of clustering, that should be enough
            sums = {}
            counts = {}

            for c in colors:
                sums[c] = [0, 0, 0]
                counts[c] = 0

            total = 0
            pixel_sum = 0
            for x in range(0, self.resized.size[0], 2):
                for y in range(0, self.resized.size[1], 2):
                    total += 4
                    pixel = self.img_data[x, y]
                    if not tuple == type(pixel):
                        pixel = (pixel, pixel, pixel)
                    pixel_sum += sum(pixel) / 3
                    color1 = min((DominantColors.diff(c, pixel), c) for c in colors)[1]
                    if len(colors) > 1:
                        color2 = min(
                            (DominantColors.diff(c, pixel), c) for c in colors if c != color1
                        )[1]
                    else:
                        color2 = color1
                    for i in [0, 1, 2]:
                        sums[color1][i] += 3 * pixel[i]
                        sums[color2][i] += 1 * pixel[i]
                    counts[color1] += 3
                    counts[color2] += 1

            colors = [c for c in colors if counts[c] > 0]
            if counter == iterations - 1:
                colors = [
                    (
                        counts[c],
                        (sums[c][0] // counts[c], sums[c][1] // counts[c], sums[c][2] // counts[c]),
                    )
                    for c in colors
                ]
            else:
                colors = [
                    (sums[c][0] // counts[c], sums[c][1] // counts[c], sums[c][2] // counts[c])
                    for c in colors
                ]

        s = sorted(colors, key=lambda x: x[0], reverse=True)
        return total, s, pixel_sum * 4 // total, self.get_width(), self.get_height()

    @staticmethod
    def contains_color(dominant_colors, color, fuzziness):
        total, colors, _, _, _ = dominant_colors
        #        colors = [x for x in colors if x[0] > total / (40 + fuzziness * 40)]
        for position, c in enumerate(colors[:3]):
            if (
                DominantColors.diff(c[1], color)
                < 1000 + (fuzziness * 1000) + max(0, 5 - position) * 300
            ):
                return True
        return False

    @staticmethod
    def close_colors(c1, c2, fuzziness):
        return DominantColors.diff(c1, c2) < 2000 + (fuzziness * 1000)

    @staticmethod
    def diff(c1, c2):
        return sum((c1[i] - c2[i]) ** 2 for i in [0, 1, 2])


if __name__ == "__main__":
    pc = DominantColors(sys.argv[1])
    print(pc.get_dominant_colors())
