import os
import abc
from jumble.IPlugin import IPlugin
from variety.Util import Util


class IVarietyPlugin(IPlugin, metaclass=abc.ABCMeta):
    """
    Variety-specific plugin interface
    """
    def activate(self):
        super(IVarietyPlugin, self).activate()
        self.config_folder = os.path.join(self.jumble.parent.config_folder, "pluginconfig/" + os.path.basename(self.folder))
        Util.makedirs(self.config_folder)

    def get_config_folder(self):
        """
        :return: The config directory which the plugin can use to store config or cache files
        """
        return self.config_folder
