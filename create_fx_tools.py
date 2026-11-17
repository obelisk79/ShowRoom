# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
"""Commands switching the viewport effects of the active document on and off.

The settings themselves are properties of the scene configuration object, so
they are saved with the document and can be fine tuned in the property editor.
"""
import FreeCAD

from Utils.resource_utils import iconPath
import create_scene_config
from create_light import inTransaction

TOOLBAR = 'ShowRoom effects'


def _castingLights(doc):
    return [o for o in doc.Objects
            if getattr(getattr(o, 'Proxy', None), 'isDisplayToolsLight', False)
            and getattr(o, 'CastShadows', False)]


def toggleShadows(doc):
    from SceneFX import shadows
    from CoinLights import directional_light
    if not shadows.available():
        FreeCAD.Console.PrintError("ShowRoom: this FreeCAD build has no Coin shadow support.\n")
        return
    cfg = create_scene_config.getSceneFolder(doc, create=True)
    cfg.Shadows = not cfg.Shadows
    if cfg.Shadows and not _castingLights(doc):
        # shadows need a light to be cast by
        sun = directional_light.createDirectionalLight(doc, "Sun")
        sun.Intensity = 0.4      # on top of FreeCAD's headlight: more would burn the picture out
        FreeCAD.Console.PrintMessage(
            "ShowRoom: added the directional light 'Sun' to cast the shadows.\n")


def toggleAmbientOcclusion(doc):
    from SceneFX import ambient_occlusion
    if not ambient_occlusion.available():
        FreeCAD.Console.PrintError("ShowRoom: ambient occlusion needs a newer pivy/Coin.\n")
        return
    cfg = create_scene_config.getSceneFolder(doc, create=True)
    cfg.AmbientOcclusion = not cfg.AmbientOcclusion


class ToggleShadowsCommand:
    toolbarName = TOOLBAR
    commandName = 'ShowRoom_ToggleShadows'

    def GetResources(self):
        return {'MenuText': "Toggle shadows",
                'ToolTip': "Switch real-time shadows on or off in the 3D views of this document.\n"
                           "Shadows are cast by the directional and spot lights with CastShadows "
                           "enabled; the settings are in the scene configuration",
                'Pixmap': iconPath('ToggleShadows.svg')}

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        inTransaction(doc, "Toggle shadows", lambda: toggleShadows(doc))

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None


class ToggleAmbientOcclusionCommand:
    toolbarName = TOOLBAR
    commandName = 'ShowRoom_ToggleAmbientOcclusion'

    def GetResources(self):
        return {'MenuText': "Toggle ambient occlusion",
                'ToolTip': "Switch screen space ambient occlusion on or off in the 3D views of "
                           "this document: creases, holes and contact areas get darker.\n"
                           "The settings are in the scene configuration",
                'Pixmap': iconPath('ToggleAmbientOcclusion.svg')}

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        inTransaction(doc, "Toggle ambient occlusion", lambda: toggleAmbientOcclusion(doc))

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None


def toggleShadowCatcher(doc):
    cfg = create_scene_config.getSceneFolder(doc, create=True)
    cfg.ShadowCatcher = not cfg.ShadowCatcher


class ToggleShadowCatcherCommand:
    toolbarName = TOOLBAR
    commandName = 'ShowRoom_ToggleShadowCatcher'

    def GetResources(self):
        return {'MenuText': "Toggle shadow catcher",
                'ToolTip': "Show the soft shadow of the model on an invisible ground, at the "
                           "lowest point of the scene.\nIt follows the first light that casts "
                           "shadows and costs nothing while navigating",
                'Pixmap': iconPath('ToggleShadowCatcher.svg')}

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        inTransaction(doc, "Toggle shadow catcher", lambda: toggleShadowCatcher(doc))

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None


class TurntableCommand:
    toolbarName = TOOLBAR
    commandName = 'ShowRoom_Turntable'

    def GetResources(self):
        return {'MenuText': "Toggle turntable",
                'ToolTip': "Start or stop a slow rotation of the view around the model, with "
                           "the effects kept on. Handy for screen recordings.\nThe speed is "
                           "TurntablePeriod in the scene configuration",
                'Pixmap': iconPath('Turntable.svg')}

    def Activated(self):
        import FreeCADGui
        from SceneFX import turntable
        from Utils import view_utils
        if turntable.is_running():
            turntable.stop()
            return
        doc = FreeCAD.ActiveDocument
        view = FreeCADGui.ActiveDocument.ActiveView
        if not hasattr(view, 'getCameraNode'):
            view = view_utils.first_view(doc)       # the active tab is not a 3D view
        if view is not None:
            turntable.start(view, doc)

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None


import showroom_toolbars     # noqa: E402
_manager = showroom_toolbars.toolbarManager
_manager.registerCommand(ToggleShadowsCommand())
_manager.registerCommand(ToggleShadowCatcherCommand())
_manager.registerCommand(ToggleAmbientOcclusionCommand())
_manager.addSeparator(TOOLBAR)
_manager.registerCommand(TurntableCommand())
