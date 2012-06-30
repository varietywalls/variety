from PIL import Image, ImageFilter
import sys

class DominantColors():
    def __init__(self, imageName):
        self.pic = Image.open(imageName)
        self.pic = self.pic.resize((50, 50))
        # self.pic = self.pic.filter(ImageFilter.BLUR)

        # load image data
        self.imgData = self.pic.load()

    def get_dominant(self):
        colors = [(0,0,0),(128, 128, 128), (192, 192, 192), (255, 255, 255), (128, 0, 0), (255, 0, 0), (128, 128, 0), (255, 255, 0),
            (0, 128, 0), (0, 255, 0), (0, 128, 128), (0, 255, 255), (0, 0, 128), (0, 0, 255), (128, 0, 128), (255, 0, 255)]

        for counter in xrange(3):
            sums = {}
            counts = {}

            for c in colors:
                sums[c] = [0, 0, 0]
                counts[c] = 0

            total = 0
            for x in xrange(0, self.pic.size[0], 1):
                for y in xrange(0, self.pic.size[1], 1):
                    total += 4
                    pixel = self.imgData[x, y]
                    color1 = min((DominantColors.diff(c, pixel), c) for c in colors)[1]
                    color2 = min((DominantColors.diff(c, pixel), c) for c in colors if c != color1)[1]
                    color3 = min((DominantColors.diff(c, pixel), c) for c in colors if c != color1 and c != color2)[1]
                    for i in [0,1,2]:
                       sums[color1][i] += 3*pixel[i]
                       sums[color2][i] += 1*pixel[i]
                       #sums[color3][i] += 1*pixel[i]
                    counts[color1] = counts[color1] + 3
                    counts[color2] = counts[color2] + 1
                    #counts[color3] = counts[color3] + 1

            colors = [c for c in colors if counts[c] > 0]
            if counter == 2:
                colors = map(lambda c: (counts[c], (sums[c][0] // counts[c], sums[c][1] // counts[c], sums[c][2] // counts[c])), colors)
            else:
                colors = map(lambda c: (sums[c][0] // counts[c], sums[c][1] // counts[c], sums[c][2] // counts[c]), colors)

        s = sorted(colors, key=lambda x: x[0], reverse=True)
        s = [x for x in s if x[0] >= total / 50]
        # print s
        return s

    @staticmethod
    def contains_color(dominant_colors, color):
        for c in dominant_colors:
            if DominantColors.close_colors(c[1], color):
                return True
        return False

    @staticmethod
    def close_colors(c1, c2):
        return DominantColors.diff(c1, c2) < 2000

    @staticmethod
    def diff(c1, c2):
        return sum((c1[i] - c2[i])**2 for i in [0,1,2])
    
if __name__ == '__main__':
    pc = DominantColors(sys.argv[1])
    print pc.get_dominant()

