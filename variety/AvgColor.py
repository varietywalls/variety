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
    print pc.averagePixels()

