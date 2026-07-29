# Running Variety on Windows

Variety now runs natively on Windows, on top of a real Windows-native GTK3 build
provided by [MSYS2](https://www.msys2.org/) - no WSL, no Linux VM, no Cygwin.
This is a young port; please report issues and mention you're on Windows.

## Setup

1. **Install MSYS2**: https://www.msys2.org/ (or `winget install MSYS2.MSYS2`).
   No admin rights or reboot required.

2. **Install the GTK3/Python/gexiv2 toolchain.** Open "MSYS2 UCRT64" from the
   Start menu (or run `C:\msys64\usr\bin\bash.exe -lc "..."`) and run:

   ```bash
   pacman -Syu   # first run will ask you to restart the shell, do that and rerun
   pacman -S mingw-w64-ucrt-x86_64-gtk3 mingw-w64-ucrt-x86_64-python \
             mingw-w64-ucrt-x86_64-python-gobject mingw-w64-ucrt-x86_64-python-cairo \
             mingw-w64-ucrt-x86_64-gexiv2 mingw-w64-ucrt-x86_64-python-pip \
             mingw-w64-ucrt-x86_64-python-requests mingw-w64-ucrt-x86_64-python-pillow \
             mingw-w64-ucrt-x86_64-python-beautifulsoup4 mingw-w64-ucrt-x86_64-python-lxml \
             mingw-w64-ucrt-x86_64-python-httplib2 mingw-w64-ucrt-x86_64-libnotify \
             mingw-w64-ucrt-x86_64-imagemagick
   ```

3. **Create a venv with access to those system packages** (pip can't install
   GTK/GObject bindings itself - they're tied to native DLLs pacman installs):

   ```bash
   /ucrt64/bin/python.exe -m venv --system-site-packages /path/to/venv
   /path/to/venv/bin/python.exe -m pip install configobj
   ```

   (`dbus-python` from `pyproject.toml` is intentionally skipped - see
   "What's different" below.)

4. **Run it**, from a checkout of this repo:

   ```bash
   /path/to/venv/bin/python.exe path/to/variety/run_variety.py
   ```

   For a normal double-click launcher with no console window, point a
   shortcut (or a `.bat` using `start "" "...\venv\bin\pythonw.exe" ...`) at
   `pythonw.exe` instead of `python.exe`.

5. **Autostart**: Preferences -> General -> the autostart checkbox now writes
   a `.vbs` launcher into your Windows Startup folder instead of a Linux
   `.desktop` file.

## What's different on Windows

Windows has no D-Bus, no gsettings, no libnotify daemon, and no XDG autostart
convention, so a handful of things are implemented differently rather than
simply disabled:

- **Wallpaper get/set**: `SystemParametersInfoW` + registry
  (`Util.set_windows_wallpaper` / `get_windows_wallpaper`) instead of the
  `set_wallpaper`/`get_wallpaper` shell scripts.
- **Lock screen**: the WinRT `Windows.System.UserProfile.LockScreen` API
  (`Util.set_windows_lock_screen`), invoked through PowerShell's built-in WinRT
  projection support so no extra Python package is required. Note some
  managed/corporate machines restrict this via policy - the call is wrapped
  and logged, not fatal, if that happens.
- **Single instance + IPC** (used for `--profile`, passing a `variety://` URL
  to an already-running instance, etc.): a loopback TCP socket with a
  per-profile shared-secret token (`variety/win_ipc.py`), since there's no
  session bus to piggyback on.
- **Desktop notifications**: shown via libnotify when available; caught and
  logged (not fatal) when there's no notification service listening.
- **Tray icon**: falls back to `Gtk.StatusIcon` (no AppIndicator on Windows).
  Its popup menu is positioned at the pointer rather than via
  `Gtk.StatusIcon.position_menu`, which miscalculates the icon's screen
  geometry under the GTK win32 backend.
- **Autostart**: a `.vbs` script in the Startup folder instead of a
  `~/.config/autostart/*.desktop` file.
- **Open file/folder, edit config**: `os.startfile` / `notepad` instead of
  `xdg-open` / `gedit`.

## Known gaps

- The "Fortune" quotes source needs the Linux `fortune` binary; it's skipped
  cleanly (not an error) when unavailable, which is always the case on
  Windows unless you separately install a fortune-mod port.
- `variety-slideshow` isn't packaged for Windows.
