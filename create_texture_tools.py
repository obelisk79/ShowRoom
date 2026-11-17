# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
import FreeCAD
import FreeCADGui

from Utils.resource_utils import iconPath

TOOLBAR = 'ShowRoom appearance'


def _owners():
    """The selected objects, a PartDesign feature standing for its Body."""
    from SceneFX import textures
    owners = []
    for obj in FreeCADGui.Selection.getSelection():
        owner = textures.texture_owner(obj)
        if owner not in owners and getattr(owner, 'ViewObject', None) is not None:
            owners.append(owner)
    return owners


def open_appearance_panel(owners):
    """Appearance panel (colour, lines, points, texture) for ``owners``."""
    from dtpanels import bridge, models
    owners = [o for o in owners if hasattr(o, 'Shape') or hasattr(o, 'Tip')]
    if not owners:
        FreeCAD.Console.PrintWarning("ShowRoom: select the objects first.\n")
        return None
    if FreeCADGui.Control.activeDialog():
        FreeCAD.Console.PrintWarning("ShowRoom: close the open task panel first.\n")
        return None
    return bridge.open_panel(models.AppearanceModel(owners))


open_texture_panel = open_appearance_panel      # older name, kept for scripts


class AppearanceCommand:
    toolbarName = TOOLBAR
    commandName = 'ShowRoom_Appearance'

    def GetResources(self):
        return {'MenuText': "Appearance…",
                'ToolTip': "Color, transparency, lines, points and texture (wood, metal, ...) of "
                           "the selected objects, in the task panel.\n"
                           "Texture images are stored in the document",
                'Pixmap': iconPath('Appearance.svg')}

    def Activated(self):
        open_appearance_panel(_owners())

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None and bool(FreeCADGui.Selection.getSelection())


import showroom_toolbars     # noqa: E402
showroom_toolbars.toolbarManager.registerCommand(AppearanceCommand())
