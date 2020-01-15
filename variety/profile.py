import os

from variety.Util import Util
from gi.repository import GLib

DEFAULT_PROFILE_PATH = os.path.join(GLib.get_user_config_dir(), "variety")

__profile_path = DEFAULT_PROFILE_PATH


def set_profile_path(profile_path):
    if not profile_path:
        profile_path = DEFAULT_PROFILE_PATH

    # if just a name is passed instead of a full path, put it under ~/.config/variety-profiles
    if not os.sep in profile_path:
        profile_path = os.path.join(GLib.get_user_config_dir(), "variety-profiles", profile_path)

    # make sure profile path has a trailing slash
    if not profile_path.endswith(os.sep):
        profile_path += os.sep

    global __profile_path
    __profile_path = profile_path


def get_profile_path(expanded=True):
    global __profile_path
    return os.path.expanduser(__profile_path) if expanded else __profile_path


def get_profile_short_name():
    return os.path.basename(get_profile_path()[:-1])


def get_profile_wm_class():
    return "Variety" + ("" if is_default_profile() else " (Profile: {})".format(get_profile_path()))


def is_default_profile():
    """
    Are we using the default profile or a custom profile?
    """
    return os.path.normpath(get_profile_path()) == os.path.normpath(
        os.path.expanduser(DEFAULT_PROFILE_PATH)
    )


def get_profile_id():
    """
    Returns a dbus-and-filename-friendly identificator of the profile path
    """
    return Util.md5(os.path.normpath(get_profile_path()))[:10]


def get_desktop_file_name():
    if is_default_profile():
        return "variety.desktop"
    else:
        return "variety-{}-{}.desktop".format(get_profile_short_name(), get_profile_id())


def get_autostart_file_path():
    return os.path.join(GLib.get_user_config_dir(), "autostart", get_desktop_file_name())
