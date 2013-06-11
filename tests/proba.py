from gi.repository import Gtk, Gio

class HelloWorldApp(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self, application_id="apps.test.helloworld",
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self.on_activate)

    def on_activate(self, data=None):
        window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        window.set_title("Gtk3 Python Example")
        window.set_border_width(24)
        label = Gtk.Label("Hello World!")
        window.add(label)
        window.show_all()
        self.add_window(window)

if __name__ == "__main__":
    app = HelloWorldApp()
    app.run(None)

#from gi.repository import Gtk, Gdk, GObject # pylint: disable=E0611
#import signal
#
#sigint_count = 0
#def sigint_handler(*args):
#    global sigint_count
#    sigint_count += 1
#    print "Terminating signal received, quitting... " + str(sigint_count)
#
#def main():
##    # Ctrl-C
#    signal.signal(signal.SIGINT, sigint_handler)
#    signal.signal(signal.SIGTERM, sigint_handler)
#    signal.signal(signal.SIGQUIT, sigint_handler)
#    #
#    #    GObject.threads_init()
#    #    Gdk.threads_init()
#    #    Gdk.threads_enter()
#    w = Gtk.Window()
#    w.connect("delete-event", Gtk.main_quit)
#    w.show_all()
#    Gtk.main()
#    #    Gdk.threads_leave()
#
#main()