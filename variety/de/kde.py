import dbus

class DE:
    def set_desktop_wallpaper(wallpaper, original_file, refresh_level, display_mode, desktop):
        jscript = """
        var allDesktops = desktops();
        d = allDesktops[%d];
        d.wallpaperPlugin = "%s";
        d.currentConfigGroup = Array("Wallpaper", "%s", "General");
        d.writeConfig("Image", "file://%s")
        """
        bus = dbus.SessionBus()
        plasma = dbus.Interface(bus.get_object('org.kde.plasmashell', '/PlasmaShell'), dbus_interface='org.kde.PlasmaShell')
        plasma.evaluateScript(jscript % (desktop, 'org.kde.image', 'org.kde.image', wallpaper))