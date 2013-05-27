import os
import imp
import logging
import inspect
from IPlugin import IPlugin

logger = logging.getLogger("variety")

class Plugit:
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
            name = os.path.splitext(f)[0]
            info = imp.find_module(name, [location])
            try:
                yield imp.load_module(name, *info)
            except Exception:
                logger.exception("Could not load plugin module %s" % os.path.join(location, f))
                continue

    def walk_plugin_classes(self):
        for module in self.walk_modules():
            def is_plugin(cls):
                return inspect.isclass(cls) and issubclass(cls, IPlugin) and cls.__module__ == module.__name__
            for name, cls in inspect.getmembers(module, is_plugin):
                yield cls

    def load(self):
        self.plugins = []
        for cls in self.walk_plugin_classes():
            try:
                plugin = cls()
                info = plugin.get_info()
                plugin.plugit = self
            except Exception:
                logger.exception("Could not get info for plugin %s" % str(cls))
                continue

            self.plugins.append((plugin, cls, info))

    def get_plugins(self, type=None):
        return [{"plugin": plugin, "class": cls, "info": info} for
            (plugin, cls, info) in self.plugins if not type or issubclass(cls, type)]
