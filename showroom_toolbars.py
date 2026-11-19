# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
from collections import OrderedDict

import FreeCADGui

SEPARATOR = "Separator"     # understood natively by FreeCAD's toolbars and menus


class ShowRoomToolbarManager:
    def __init__(self):
        self.Toolbars = OrderedDict()   # toolbar name -> list of command names

    def registerCommand(self, command):
        FreeCADGui.addCommand(command.commandName, command)
        self.Toolbars.setdefault(command.toolbarName, []).append(command.commandName)

    def addSeparator(self, toolbarName):
        self.Toolbars.setdefault(toolbarName, []).append(SEPARATOR)


toolbarManager = ShowRoomToolbarManager()

# importing the command modules registers their commands
import create_light          # noqa: E402,F401
import create_helper_tools   # noqa: E402,F401
import create_fx_tools       # noqa: E402,F401
import create_texture_tools  # noqa: E402,F401
import spaceNav_tools        # noqa: E402,F401
import create_settings_tools  # noqa: E402,F401
