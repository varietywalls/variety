class IPlugin(object):
    """
  The most simple interface to be inherited when creating a plugin.
  """
    @classmethod
    def get_info(cls):
        return {}
#        return {
#            "name": None,
#            "description": None,
#            "version": None,
#            "author": None,
#            "url": None
#        }

    def __init__(self):
        """
       Set the basic variables.
       """
        self.plugit = None
        self.is_activated = False

    def activate(self):
        """
       Called at plugin activation.
       """
        self.is_activated = True

    def deactivate(self):
        """
       Called when the plugin is disabled.
       """
        self.is_activated = False

