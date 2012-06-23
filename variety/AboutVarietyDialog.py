# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

import gettext
from gettext import gettext as _
gettext.textdomain('variety')

import logging
logger = logging.getLogger('variety')

from variety_lib.AboutDialog import AboutDialog

# See variety_lib.AboutDialog.py for more details about how this class works.
class AboutVarietyDialog(AboutDialog):
    __gtype_name__ = "AboutVarietyDialog"
    
    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the about dialog"""
        super(AboutVarietyDialog, self).finish_initializing(builder)

        # Code for other initialization actions should be added here.

