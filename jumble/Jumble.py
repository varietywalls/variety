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

import os
import imp
import logging
import inspect
from IPlugin import IPlugin

class Jumble:
    def __init__(self, folders):
        self.folders = folders

    def walk_python_files(self):
        for folder in self.folders:
            for location, directories, filenames in os.walk(folder):
                for f in filenames:
                    if f.endswith(".py"):
                        yield location, f

    def walk_modules(self):
        for location, f in self.walk_python_files():
            path = os.path.join(location, f)
            name = os.path.splitext(f)[0]
            info = imp.find_module(name, [location])
            try:
                yield imp.load_module(name, *info), path
            except Exception:
                logging.exception("Could not load plugin module %s" % path)
                continue

    def walk_plugin_classes(self):
        for module, path in self.walk_modules():
            def is_plugin(cls):
                return inspect.isclass(cls) and issubclass(cls, IPlugin) and cls.__module__ == module.__name__
            for name, cls in inspect.getmembers(module, is_plugin):
                yield cls, path

    def load(self):
        self.plugins = []
        for cls, path in self.walk_plugin_classes():
            try:
                info = cls.get_info()
                plugin = cls()
                plugin.jumble = self
                plugin.path = os.path.realpath(path)
                plugin.folder = os.path.dirname(plugin.path)
            except Exception:
                logging.exception("Could not get info for cadidate plugin class %s" % str(cls))
                continue

            self.plugins.append({"plugin": plugin, "class": cls, "info": info})

    def get_plugins(self, type=None, typename=None, name=None):
        return [p for p in self.plugins if
                (not type or issubclass(p["class"], type)) and
                (not typename or p["class"].__name__ == typename) and
                (not name or p["info"].name == name)]

