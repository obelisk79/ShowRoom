# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
import FreeCAD

from Utils.resource_utils import iconPath
import create_scene_config
from CoinLights import point_light, directional_light, spot_light, rigs

TOOLBAR = 'ShowRoom lights'


def inTransaction(doc, name, function):
    """Run ``function`` as one undoable step (or as part of the open task panel's)."""
    import FreeCADGui
    if FreeCADGui.Control.activeDialog():
        result = function()
        doc.recompute()
        return result
    doc.openTransaction(name)
    try:
        result = function()
    except Exception:
        doc.abortTransaction()
        raise
    doc.commitTransaction()
    doc.recompute()
    return result


def createAndEdit(doc, name, function):
    """Create an object and open its task panel; Cancel deletes it again, as in Part Design."""
    import FreeCADGui
    from dtpanels import bridge
    if FreeCADGui.Control.activeDialog():
        return inTransaction(doc, name, function)
    doc.openTransaction(name)
    try:
        obj = function()
        doc.recompute()
    except Exception:
        doc.abortTransaction()
        raise
    bridge.mark_new(obj)
    if not bridge.edit(obj):
        doc.commitTransaction()
    return obj


class _DocumentCommand:
    def IsActive(self):
        return FreeCAD.ActiveDocument is not None


def _new_scene(doc):
    from SceneFX import autoscene
    cfg = create_scene_config.createSceneFolder(doc)
    autoscene.apply_defaults(cfg)
    return cfg


class CreateSceneConfigCommand(_DocumentCommand):
    toolbarName = TOOLBAR
    commandName = 'ShowRoom_SceneConfig'

    def GetResources(self):
        return {'MenuText': "Scene settings…",
                'ToolTip': "Open the scene settings in the task panel: shadows, shadow catcher, "
                           "ambient occlusion, lights, turntable.\nThe first time, it creates the "
                           "scene configuration folder that holds the lights and the grid",
                'Pixmap': iconPath('CreateCustomScene.svg')}

    def Activated(self):
        import FreeCADGui
        from dtpanels import bridge
        doc = FreeCAD.ActiveDocument
        if FreeCADGui.Control.activeDialog():
            FreeCAD.Console.PrintWarning("ShowRoom: close the open task panel first.\n")
            return
        cfg = create_scene_config.getSceneFolder(doc)
        if cfg is None:
            createAndEdit(doc, "Scene settings", lambda: _new_scene(doc))
        else:
            bridge.edit(cfg)


class CreatePointLightCommand(_DocumentCommand):
    toolbarName = TOOLBAR
    commandName = 'ShowRoom_PointLight'

    def GetResources(self):
        return {'MenuText': "Create point light",
                'ToolTip': "Add a light that shines in every direction from one point",
                'Pixmap': iconPath('CreatePointLight.svg')}

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        createAndEdit(doc, "Create point light", lambda: point_light.createPointLight(doc))


class CreateDirectionalLightCommand(_DocumentCommand):
    toolbarName = TOOLBAR
    commandName = 'ShowRoom_DirectionalLight'

    def GetResources(self):
        return {'MenuText': "Create directional light",
                'ToolTip': "Add a light with parallel rays, like the sun. It can cast shadows",
                'Pixmap': iconPath('CreateDirectionalLight.svg')}

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        createAndEdit(doc, "Create directional light",
                      lambda: directional_light.createDirectionalLight(doc))


class CreateSpotLightCommand(_DocumentCommand):
    toolbarName = TOOLBAR
    commandName = 'ShowRoom_SpotLight'

    def GetResources(self):
        return {'MenuText': "Create spot light",
                'ToolTip': "Add a light that shines in a cone. It can cast shadows",
                'Pixmap': iconPath('CreateSpotLight.svg')}

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        createAndEdit(doc, "Create spot light", lambda: spot_light.createSpotLight(doc))


class _RigCommand(_DocumentCommand):
    text = tip = icon = transaction = ""

    def create(self, doc):
        raise NotImplementedError()

    def GetResources(self):
        return {'MenuText': self.text, 'ToolTip': self.tip, 'Pixmap': iconPath(self.icon)}

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        inTransaction(doc, self.text, lambda: self.create(doc))


class ThreePointRigCommand(_RigCommand):
    commandName = 'ShowRoom_RigThreePoint'
    text = "Three-point lighting"
    tip = ("Add a key light (casting the shadows), a fill light and a rim light, "
           "placed for the current view")
    icon = 'RigThreePoint.svg'

    def create(self, doc):
        return rigs.createThreePoint(doc)


class StudioRigCommand(_RigCommand):
    commandName = 'ShowRoom_RigStudio'
    text = "Studio lighting"
    tip = "Add a soft light from above and two side lights: even lighting for presentations"
    icon = 'RigStudio.svg'

    def create(self, doc):
        return rigs.createStudio(doc)


class SunRigCommand(_RigCommand):
    commandName = 'ShowRoom_RigSun'
    text = "Sun"
    tip = ("Add a directional light positioned with its Azimuth (compass direction) "
           "and Elevation (height above the horizon) properties")
    icon = 'RigSun.svg'

    def create(self, doc):
        return rigs.createSun(doc)


class LightRigGroupCommand(_DocumentCommand):
    """Drop-down button holding the light rigs."""
    toolbarName = TOOLBAR
    commandName = 'ShowRoom_LightRigs'
    members = (ThreePointRigCommand, StudioRigCommand, SunRigCommand)

    def GetCommands(self):
        return tuple(member.commandName for member in self.members)

    def GetDefaultCommand(self):
        return 0

    def GetResources(self):
        return {'MenuText': "Light rigs", 'ToolTip': "Add a ready-made set of lights"}


import FreeCADGui                # noqa: E402
import showroom_toolbars     # noqa: E402
_manager = showroom_toolbars.toolbarManager
_manager.registerCommand(CreateSceneConfigCommand())
_manager.addSeparator(TOOLBAR)
_manager.registerCommand(CreatePointLightCommand())
_manager.registerCommand(CreateDirectionalLightCommand())
_manager.registerCommand(CreateSpotLightCommand())
_manager.addSeparator(TOOLBAR)
for _member in LightRigGroupCommand.members:
    FreeCADGui.addCommand(_member.commandName, _member())
_manager.registerCommand(LightRigGroupCommand())
