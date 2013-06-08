import os
from jumble.IPlugin import IPlugin

class IVarietyPlugin(IPlugin):
    def get_config_folder(self):
        return os.path.join(self.jumble.parent.config_folder, "pluginconfig/" + os.path.basename(self.folder))
