import os, subprocess, json

class DE:
    def set_desktop_wallpaper(wallpaper, original_file, refresh_level, display_mode, desktop):
        pid = subprocess.run(["pgrep", "-x", "sway"], capture_output = True, text=True).stdout.strip("\n")
        os.environ["SWAYSOCK"] = "/run/user/%s/sway-ipc.%s.%s.sock" % (os.getuid(), os.getuid(), pid)
        outputs_json = subprocess.run(["swaymsg", "-t", "get_outputs"], capture_output = True, text=True).stdout.strip("\n")
        outputs = json.loads(outputs_json)
        subprocess.run(["swaymsg", "output", outputs[desktop]['name'], "bg", wallpaper, "fill"])