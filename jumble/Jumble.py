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

logger = logging.getLogger('variety')


class Jumble:
    def __init__(self, folders):
        self.folders = folders

    def _walk_python_files(self):
        for folder in self.folders:
            for location, directories, filenames in os.walk(folder):
                for f in filenames:
                    if f.endswith(".py"):
                        yield location, f

    def _walk_modules(self):
        for location, f in self._walk_python_files():
            path = os.path.join(location, f)
            name = os.path.splitext(f)[0]
            info = imp.find_module(name, [location])
            try:
                logger.info("Jumble loading module in %s from %s" % (name, path))
                yield imp.load_module(name, *info), path
            except Exception:
                logging.exception("Could not load plugin module %s" % path)
                continue

    def _walk_plugin_classes(self):
        for module, path in self._walk_modules():
            def is_plugin(cls):
                return inspect.isclass(cls) and issubclass(cls, IPlugin) and cls.__module__ == module.__name__

            for name, cls in inspect.getmembers(module, is_plugin):
                yield cls, path

    def load(self):
        """
        Loads all plugins from the plugin folders, without activating them
        """
        logger.info("Jumble loading")
        self.plugins = []
        for cls, path in self._walk_plugin_classes():
            try:
                info = cls.get_info()
            except Exception:
                logging.exception("Jumble: not a plugin class: %s" % str(cls))
                continue

            if not info:
                logging.warning("Jumble: %s: get_info() returned None" % str(cls))
                continue

            try:
                plugin = cls()
                logger.info("Jumble found plugin class: %s: %s" % (str(cls), str(info)))

                plugin.jumble = self
                plugin.path = os.path.realpath(path)
                plugin.folder = os.path.dirname(plugin.path)
                self.plugins.append({"plugin": plugin, "class": cls, "info": info})
            except Exception:
                logging.exception("Jumble: could not instantiate plugin class: %s" % str(cls))
                continue

    def get_plugins(self, clazz=None, typename=None, name=None, active=None):
        """
        Searches for plugins that match the given criteria. If no criteria are given, all loaded plugins are returned.

        :param clazz: parent plugin class; optional
        :param typename: plugin type name; optional
        :param name: plugin name, should match exactly; optional
        :param active: specifies whether the plugin should be currently active, or inactive; optional,
        by default both are returned
        :return: all matching plugins, as hashes {"plugin": plugin, "class": plugin_class, "info": info}
        """
        return sorted([p for p in self.plugins if
                       (not clazz or issubclass(p["class"], clazz)) and
                       (not typename or p["class"].__name__ == typename) and
                       (not name or p["info"]["name"] == name) and
                       (active is None or p["plugin"].is_active() == active)],
                      key=lambda p: p["info"]["name"])

