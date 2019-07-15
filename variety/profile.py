import os

from variety.Util import Util

DEFAULT_PROFILE_PATH = "~/.config/variety/"

__profile_path = DEFAULT_PROFILE_PATH


def set_profile_path(profile_path):
    if not profile_path:
        profile_path = DEFAULT_PROFILE_PATH

    # if just a name is passed instead of a full path, put it under ~/.config/variety-profiles
    if not "/" in profile_path:
        profile_path = "~/.config/variety-profiles/{}".format(profile_path)

    # make sure profile path has a trailing slash
    if not profile_path.endswith("/"):
        profile_path += "/"

    global __profile_path
    __profile_path = profile_path


def get_profile_path(expanded=True):
    global __profile_path
    return os.path.expanduser(__profile_path) if expanded else __profile_path


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
    return Util.md5(os.path.normpath(get_profile_path()))
