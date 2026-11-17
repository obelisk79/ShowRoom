# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
import FreeCAD

from Utils.resource_utils import iconPath
from SpaceNav import spacenav_commands

TOOLBAR = 'ShowRoom SpaceMouse'
NOTE = "\n(Built-in SpaceMouse support only; ignored when the 3Dconnexion driver is in control)"


class _LockCommand:
    """Checkable command: checked = the axes are locked."""
    toolbarName = TOOLBAR
    parameter = None
    what = ""

    def Activated(self, checked=None):
        if checked is None:
            locked = spacenav_commands.toggle(self.parameter)
        else:
            locked = bool(checked)
            spacenav_commands.setLocked(self.parameter, locked)
        FreeCAD.Console.PrintLog("ShowRoom: SpaceMouse %s %s\n"
                                 % (self.what, "locked" if locked else "unlocked"))

    def IsActive(self):
        return True

    def resources(self, text, tip, icon):
        return {'MenuText': text, 'ToolTip': tip + NOTE, 'Pixmap': iconPath(icon),
                'Checkable': spacenav_commands.isLocked(self.parameter)}


class SpToolsLockRot(_LockCommand):
    commandName = 'ShowRoom_SpaceNavLockRotation'
    parameter = 'Rotations'
    what = "rotation"

    def GetResources(self):
        return self.resources("Lock SpaceMouse rotation",
                              "The SpaceMouse only pans and zooms", 'SpNav.svg')


class SpToolsLockTrans(_LockCommand):
    commandName = 'ShowRoom_SpaceNavLockTranslation'
    parameter = 'Translations'
    what = "translation"

    def GetResources(self):
        return self.resources("Lock SpaceMouse translation",
                              "The SpaceMouse only rotates", 'SpNav_LockTrans.svg')


class SpToolsLockHorizon(_LockCommand):
    commandName = 'ShowRoom_SpaceNavLockHorizon'
    parameter = 'RollEnable'
    what = "roll (horizon)"

    def GetResources(self):
        return self.resources("Lock SpaceMouse horizon",
                              "The SpaceMouse does not roll the view: the horizon stays level",
                              'SpNav_LockHor.svg')


import showroom_toolbars     # noqa: E402
showroom_toolbars.toolbarManager.registerCommand(SpToolsLockRot())
showroom_toolbars.toolbarManager.registerCommand(SpToolsLockTrans())
showroom_toolbars.toolbarManager.registerCommand(SpToolsLockHorizon())
