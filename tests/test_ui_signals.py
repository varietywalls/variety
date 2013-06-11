from gi.repository import Gtk, GObject
import time

def f(w=None):
    print "AAAaaaaaaaaaaaa"

def r():
    print "here"
    a = Gtk.FileChooserButton()
    a.connect("selection-changed", f)
    a.set_filename(str(time.time()))
    print "here2"

GObject.idle_add(r)
Gtk.main()
