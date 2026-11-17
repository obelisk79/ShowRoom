# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
import FreeCAD

from Utils.resource_utils import iconPath
from HelperTools import dynamic_grid
from create_light import createAndEdit

TOOLBAR = 'ShowRoom helpers'


class CreateDynamicGrid:
    toolbarName = TOOLBAR
    commandName = 'ShowRoom_DynamicGrid'

    def GetResources(self):
        return {'MenuText': 'Create dynamic grid',
                'ToolTip': 'Add a reference grid that follows the lowest point of the visible scene',
                'Pixmap': iconPath('CreateDynamicGrid.svg')}

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        createAndEdit(doc, "Create dynamic grid", lambda: dynamic_grid.createDynamicGrid(doc))

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None


import showroom_toolbars     # noqa: E402
showroom_toolbars.toolbarManager.registerCommand(CreateDynamicGrid())
