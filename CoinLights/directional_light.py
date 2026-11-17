# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
import math

import FreeCAD
from pivy import coin

from CoinLights import universal_light
from Utils import view_utils
from Utils.resource_utils import iconPath

DEFAULT_DIRECTION = (0.35, 0.6, -1.0)


class DirectionalLight(universal_light.UniversalLight):
    type = 'DirectionalLight'
    canCastShadows = True
    defaultCastShadows = True

    def setProperties(self, obj):
        super().setProperties(obj)
        pl = obj.PropertiesList
        if 'Direction' not in pl:
            obj.addProperty("App::PropertyVector", "Direction", "Light",
                            "The direction the light travels in"
                            ).Direction = FreeCAD.Vector(*DEFAULT_DIRECTION).normalize()
        if 'GizmoPosition' not in pl:
            obj.addProperty("App::PropertyVector", "GizmoPosition", "Manipulator",
                            "Where the manipulator is drawn. A directional light has no "
                            "position: this does not change the lighting")
        universal_light.hideLegacy(obj)


        if 'Azimuth' not in pl:
            obj.addProperty("App::PropertyAngle", "Azimuth", "Sun position",
                            "Compass direction the light comes from: 0 = from +Y, 90 = from +X. "
                            "Linked to Direction")
            obj.addProperty("App::PropertyAngle", "Elevation", "Sun position",
                            "Height of the light above the horizon, in degrees. "
                            "Linked to Direction")
            self.directionToAngles(obj)

    # Direction and Azimuth/Elevation describe the same thing: changing one
    # updates the other.  The comparisons are what stops the ping-pong.
    @staticmethod
    def anglesOf(direction):
        source = FreeCAD.Vector(direction).negative()
        if source.Length < 1e-9:
            return None
        source.normalize()
        elevation = math.degrees(math.asin(max(-1.0, min(1.0, source.z))))
        if abs(source.x) < 1e-9 and abs(source.y) < 1e-9:
            return None, elevation           # straight up or down: any azimuth
        return math.degrees(math.atan2(source.x, source.y)) % 360.0, elevation

    @staticmethod
    def directionOf(azimuth, elevation):
        az, el = math.radians(azimuth), math.radians(elevation)
        return FreeCAD.Vector(-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el),
                              -math.sin(el))

    def directionToAngles(self, obj):
        angles = self.anglesOf(obj.Direction)
        if angles is None:
            return
        azimuth, elevation = angles
        if azimuth is not None and abs((obj.Azimuth.Value - azimuth + 180) % 360 - 180) > 1e-3:
            obj.Azimuth = azimuth
        if abs(obj.Elevation.Value - elevation) > 1e-3:
            obj.Elevation = elevation

    def onChanged(self, obj, prop):
        if prop not in ('Direction', 'Azimuth', 'Elevation') or 'Restore' in obj.State:
            return
        if not all(hasattr(obj, name) for name in ('Direction', 'Azimuth', 'Elevation')):
            return
        if prop == 'Direction':
            self.directionToAngles(obj)
        else:
            elevation = max(-90.0, min(90.0, obj.Elevation.Value))
            wanted = self.directionOf(obj.Azimuth.Value, elevation)
            current = FreeCAD.Vector(obj.Direction)
            if current.Length > 1e-9:
                current.normalize()
            if not wanted.isEqual(current, 1e-5):
                obj.Direction = wanted


class ViewProviderDirectionalLight(universal_light.ViewProviderUniversalLight):
    def createLightInstance(self):
        # The shadow casting flavour is an ordinary directional light as long
        # as it is not inside a shadow group.
        node = view_utils.new_node('SoShadowDirectionalLight', keep=True)
        return node if node is not None else coin.SoDirectionalLight()

    def getIcon(self):
        return iconPath("CreateDirectionalLight.svg")


def createDirectionalLight(doc=None, name="DirectionalLight"):
    doc = doc or FreeCAD.ActiveDocument
    center, size = universal_light.sceneExtent(doc)
    obj = doc.addObject("App::FeaturePython", name)
    DirectionalLight(obj)
    if size > 0:
        # draw the gizmo above the scene, on the side the light comes from
        obj.GizmoPosition = center - obj.Direction * (0.8 * size)
    if FreeCAD.GuiUp:
        ViewProviderDirectionalLight(obj.ViewObject)
    universal_light.addToScene(obj)
    return obj


def placeGizmo(obj):
    """Draw the gizmo above the scene, on the side the light comes from."""
    center, size = universal_light.sceneExtent(obj.Document)
    if size > 0:
        direction = FreeCAD.Vector(obj.Direction)
        if direction.Length > 1e-9:
            direction.normalize()
        obj.GizmoPosition = center - direction * (0.8 * size)


if __name__ == "__main__":
    createDirectionalLight()
