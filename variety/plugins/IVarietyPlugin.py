import os
from jumble.IPlugin import IPlugin

class IVarietyPlugin(IPlugin):
    """
    Variety-specific plugin interface
    """

    def get_config_folder(self):
        """
        :return: The config directory which the plugin can use to store config or cache files
        """
        return os.path.join(self.jumble.parent.config_folder, "pluginconfig/" + os.path.basename(self.folder))
