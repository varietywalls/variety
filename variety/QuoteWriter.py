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

import cairo
from PIL import Image
from gi.repository import Gdk, Pango, PangoCairo, GdkPixbuf
from variety.Util import Util

class QuoteWriter:

    @staticmethod
    def write_quote(quote, author, infile, outfile, options = None):
        w, h = Util.get_scaled_size(infile)
        surface = QuoteWriter.load_cairo_surface(infile, w, h)
        QuoteWriter.write_quote_on_surface(surface, quote, author, options)
        QuoteWriter.save_cairo_surface(surface, outfile)

    @staticmethod
    def load_cairo_surface(filename, w, h):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, w, h)
        surface = cairo.ImageSurface(0, pixbuf.get_width(), pixbuf.get_height())
        context = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
        context.paint()
        return surface

    @staticmethod
    def save_cairo_surface(surface, filename):
        size = surface.get_width(), surface.get_height()
        image = Image.frombuffer('RGBA', size, surface.get_data(), 'raw', 'BGRA', 0, 1)
        image.save(filename, quality=100)

    @staticmethod
    def write_quote_on_surface(surface, quote, author, options = None, margin = 30):
        qcontext = cairo.Context(surface)
        acontext = cairo.Context(surface)

        sw = surface.get_width()
        sh = surface.get_height()

        trimw = Util.compute_trimmed_offsets((sw, sh),
            (Gdk.Screen.get_default().get_width(), Gdk.Screen.get_default().get_height()))[0]

        width = (sw - 2 * trimw) * 70 // 100 # use 70% of the visible width

        qlayout = PangoCairo.create_layout(qcontext)
        qlayout.set_width((width - 4 * margin) * Pango.SCALE)
        qlayout.set_alignment(Pango.Alignment.LEFT)
        qlayout.set_wrap(Pango.WrapMode.WORD)
        font = options.quotes_font if options else "Bitstream Charter 30"
        qlayout.set_font_description(Pango.FontDescription(font))
        qlayout.set_text(quote, -1)

        qheight = qlayout.get_pixel_size()[1]
        qwidth = qlayout.get_pixel_size()[0]
        width = qwidth + 4 * margin

        alayout = PangoCairo.create_layout(acontext)
        alayout.set_width(qwidth * Pango.SCALE)
        alayout.set_alignment(Pango.Alignment.RIGHT)
        alayout.set_wrap(Pango.WrapMode.WORD)
        alayout.set_font_description(Pango.FontDescription(font))
        alayout.set_text(author, -1)

        aheight = alayout.get_pixel_size()[1]

        height = qheight + aheight

        qcontext.set_source_rgba(0.55, 0.55, 0.55, 0.55) # gray semi-transparent background
        qcontext.rectangle(sw - width - trimw, sh//2 - height//2 - 150 - margin, 20000, height + margin * 3)
        qcontext.fill()

        qcontext.set_source_rgb(1, 1, 1)
        qcontext.translate(sw - width - trimw + 2 * margin, sh//2 - height//2 - 150)
        PangoCairo.update_layout(qcontext, qlayout)
        PangoCairo.show_layout(qcontext, qlayout)

        acontext.set_source_rgb(1, 1, 1)
        acontext.translate(sw - width - trimw + 2 * margin, sh//2 - height//2 - 150 + qheight + margin)
        PangoCairo.update_layout(acontext, alayout)
        PangoCairo.show_layout(acontext, alayout)

        qcontext.show_page()
        acontext.show_page()

if __name__ == "__main__":
    QuoteWriter.write_quote(
        '"I may be drunk, Miss, but in the morning I will be sober and you will still be ugly."',
        "Winston Churchill",
        "test.jpg",
        "test_result.jpg")
