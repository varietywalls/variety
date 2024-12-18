import subprocess

class DE:
    def set_desktop_wallpaper(wallpaper, original_file, refresh_level, display_mode, desktop):
        result = subprocess.run(["xfconf-query", "-c", "xfce4-desktop", "-p", "/backdrop", "-l"],
                                        capture_output = True,
                                        text=True).stdout.strip("\n")
        lines = result.split()
        for line in lines:
            line = line.strip()
            line_parts = line.split('/')
            if line_parts[len(line_parts) - 1] != "last-image":
                continue
            monitor_parts = line_parts[3].split('-')
            if '%d' % (desktop + 1) == monitor_parts[1]:
                subprocess.run(["xfconf-query", "-c", "xfce4-desktop", "-p", line, "-n", "-t", "string", "-s", ""])
                subprocess.run(["xfconf-query", "-c", "xfce4-desktop", "-p", line, "-s", ""])
                subprocess.run(["xfconf-query", "-c", "xfce4-desktop", "-p", line, "-s", wallpaper])