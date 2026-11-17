# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
import FreeCAD
from pivy import coin

import CoinLights.universal_light as light
from Utils import view_utils
from Utils.resource_utils import iconPath

DROP_OFF_LIMITS = (0.0, 1.0, 0.05)


class SpotLight(light.UniversalLight):
    type = 'SpotLight'
    canCastShadows = True
    defaultCastShadows = False

    def setProperties(self, obj):
        super().setProperties(obj)
        pl = obj.PropertiesList
        if 'Location' not in pl:
            obj.addProperty("App::PropertyVector", "Location", "Light",
                            "The position of the light in the scene").Location = FreeCAD.Vector(0, -1, 0)
        if 'Direction' not in pl:
            obj.addProperty("App::PropertyVector", "Direction", "Light",
                            "The direction the light points to").Direction = FreeCAD.Vector(-1, 0, 0)
        if 'CutOffAngle' not in pl:
            obj.addProperty("App::PropertyAngle", "CutOffAngle", "SpotLight",
                            "Half angle of the light cone (1 to 90 degrees)").CutOffAngle = 45.0
        if 'DropOffRate' not in pl:
            obj.addProperty("App::PropertyFloatConstraint", "DropOffRate", "SpotLight",
                            "How fast the light fades from the axis of the cone to its border"
                            ).DropOffRate = (0.0,) + DROP_OFF_LIMITS

        if 'Target' not in pl:
            obj.addProperty("App::PropertyVector", "Target", "Light",
                            "Point the spot light aims at. Moving the light keeps it aimed "
                            "there; changing Direction moves the target along the beam")
            d = FreeCAD.Vector(obj.Direction)
            if d.Length < 1e-9:
                d = FreeCAD.Vector(-1, 0, 0)
            d.normalize()
            distance = max(FreeCAD.Vector(obj.Location).Length, 50.0)
            self._syncing = True
            try:
                obj.Target = FreeCAD.Vector(obj.Location) + d * distance
            finally:
                self._syncing = False

    def onDocumentRestored(self, obj):
        super().onDocumentRestored(obj)
        light._constraint(obj, 'DropOffRate', DROP_OFF_LIMITS)

    def onChanged(self, obj, prop):
        """Keep Location, Target and Direction consistent."""
        if prop not in ('Location', 'Target', 'Direction') or getattr(self, '_syncing', False):
            return
        if 'Restore' in obj.State or not all(hasattr(obj, n) for n in ('Location', 'Target', 'Direction')):
            return
        try:
            if obj.Document.Transacting:      # undo / redo restore every property themselves
                return
        except Exception:
            pass
        self._syncing = True
        try:
            L, T = FreeCAD.Vector(obj.Location), FreeCAD.Vector(obj.Target)
            if prop in ('Location', 'Target'):
                d = T - L
                if d.Length > 1e-9:
                    d.normalize()
                    current = FreeCAD.Vector(obj.Direction)
                    if current.Length > 1e-9:
                        current.normalize()
                    if not d.isEqual(current, 1e-9):
                        obj.Direction = d
            else:
                d = FreeCAD.Vector(obj.Direction)
                if d.Length > 1e-9:
                    d.normalize()
                    distance = (T - L).Length
                    if distance < 1e-6:
                        distance = max(L.Length, 50.0)
                    target = L + d * distance
                    if not target.isEqual(T, 1e-9 * max(1.0, distance)):
                        obj.Target = target
        finally:
            self._syncing = False


class ViewProviderSpotLight(light.ViewProviderUniversalLight):
    def createLightInstance(self):
        # plain spot light outside of a shadow group, see the directional light
        node = view_utils.new_node('SoShadowSpotLight', keep=True)
        return node if node is not None else coin.SoSpotLight()

    def getIcon(self):
        return iconPath("CreateSpotLight.svg")


def createSpotLight(doc=None):
    doc = doc or FreeCAD.ActiveDocument
    center, size = light.sceneExtent(doc)
    obj = doc.addObject("App::FeaturePython", "SpotLight")
    SpotLight(obj)
    if size > 0:
        offset = FreeCAD.Vector(0.5, -0.5, 0.8) * size
        obj.Location = center + offset
        obj.Target = center                 # aim at the scene
    if FreeCAD.GuiUp:
        ViewProviderSpotLight(obj.ViewObject)
    light.addToScene(obj)
    return obj


if __name__ == "__main__":
    createSpotLight()
