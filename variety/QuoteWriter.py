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

import threading

import cairo
from PIL import Image

from variety.Util import Util

# fmt: off
import gi  # isort:skip
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gdk, GdkPixbuf, GObject, Pango, PangoCairo  # isort:skip
# fmt: on


class QuoteWriter:
    @staticmethod
    def write_quote(quote, author, infile, outfile, options=None):
        done_event = threading.Event()
        exception = [None]

        def go():
            try:
                w, h = Util.get_scaled_size(infile)
                surface = QuoteWriter.load_cairo_surface(infile, w, h)
                QuoteWriter.write_quote_on_surface(surface, quote, author, options)
                QuoteWriter.save_cairo_surface(surface, outfile)
            except Exception as e:
                exception[0] = e
            finally:
                done_event.set()

        GObject.idle_add(go)
        done_event.wait()
        if exception[0]:
            raise exception[0]  # pylint: disable=raising-bad-type

    @staticmethod
    def load_cairo_surface(filename, w, h):
        # pylint: disable=no-member
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(filename, w, h, False)
        surface = cairo.ImageSurface(0, pixbuf.get_width(), pixbuf.get_height())
        context = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(context, pixbuf, 0, 0)
        context.paint()
        return surface

    @staticmethod
    def save_cairo_surface(surface, filename):
        try:
            # attempt faster method first
            # the get_data() call will fail with Cairo version < 1.15.4-1 (e.g. on 16.04)
            # https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=809479
            data = surface.get_data()
            size = surface.get_width(), surface.get_height()
            image = Image.frombuffer("RGBA", size, data.tobytes(), "raw", "BGRA", 0, 1).convert(
                "RGB"
            )
            image.save(filename, quality=100)
        except:
            # fallback to slower method, but which works on 16.04
            surface.write_to_png(filename)

    @staticmethod
    def write_quote_on_surface(surface, quote, author=None, options=None, margin=30):
        qcontext = cairo.Context(surface)  # pylint: disable=no-member
        acontext = cairo.Context(surface)  # pylint: disable=no-member

        iw = surface.get_width()
        ih = surface.get_height()

        sw = Gdk.Screen.get_default().get_width()
        sh = Gdk.Screen.get_default().get_height()
        trimw, trimh = Util.compute_trimmed_offsets((iw, ih), (sw, sh))

        width = max(
            200, sw * options.quotes_width // 100
        )  # use quotes_width percent of the visible width

        qlayout = PangoCairo.create_layout(qcontext)
        qlayout.set_width((width - 4 * margin) * Pango.SCALE)
        qlayout.set_alignment(Pango.Alignment.LEFT)
        qlayout.set_wrap(Pango.WrapMode.WORD)
        font = options.quotes_font if options else "Bitstream Charter 30"
        qlayout.set_font_description(Pango.FontDescription(font))
        qlayout.set_text(quote, -1)

        qheight = qlayout.get_pixel_size()[1]
        qwidth = qlayout.get_pixel_size()[0]
        if options.quotes_width < 98:
            width = qwidth + 4 * margin
        else:
            width = sw

        alayout = PangoCairo.create_layout(acontext)
        aheight = 0
        if author:
            alayout.set_width(qwidth * Pango.SCALE)
            alayout.set_alignment(Pango.Alignment.RIGHT)
            alayout.set_wrap(Pango.WrapMode.WORD)
            alayout.set_font_description(Pango.FontDescription(font))
            alayout.set_text(author, -1)

            aheight = alayout.get_pixel_size()[1]

        height = qheight + aheight + 2.5 * margin

        bgc = options.quotes_bg_color
        qcontext.set_source_rgba(
            bgc[0] / 255.0, bgc[1] / 255.0, bgc[2] / 255.0, options.quotes_bg_opacity / 100.0
        )  # gray semi-transparent background

        hpos = trimw + (sw - width) * options.quotes_hpos // 100
        vpos = trimh + (sh - height) * options.quotes_vpos // 100
        qcontext.rectangle(hpos, vpos, width, height)
        qcontext.fill()

        qcontext.translate(hpos + (width - qwidth) / 2, vpos + margin)

        if options.quotes_text_shadow:
            qcontext.set_source_rgba(0, 0, 0, 0.2)
            PangoCairo.update_layout(qcontext, qlayout)
            PangoCairo.show_layout(qcontext, qlayout)
            qcontext.translate(-2, -2)

        tc = options.quotes_text_color

        qcontext.set_source_rgb(tc[0] / 255.0, tc[1] / 255.0, tc[2] / 255.0)
        PangoCairo.update_layout(qcontext, qlayout)
        PangoCairo.show_layout(qcontext, qlayout)

        acontext.translate(hpos + (width - qwidth) / 2, vpos + margin + qheight + margin / 2)

        if options.quotes_text_shadow:
            acontext.set_source_rgba(0, 0, 0, 0.2)
            PangoCairo.update_layout(acontext, alayout)
            PangoCairo.show_layout(acontext, alayout)
            acontext.translate(-2, -2)

        acontext.set_source_rgb(tc[0] / 255.0, tc[1] / 255.0, tc[2] / 255.0)
        PangoCairo.update_layout(acontext, alayout)
        PangoCairo.show_layout(acontext, alayout)

        qcontext.show_page()
        acontext.show_page()


if __name__ == "__main__":
    QuoteWriter.write_quote(
        '"I may be drunk, Miss, but in the morning I will be sober and you will still be ugly."',
        "Winston Churchill",
        "test.jpg",
        "test_result.png",
    )
