# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
"""Ready-made sets of lights.

The key and fill lights are placed relative to the way the view looks at the
model when the rig is created (as a photographer would), then stay fixed in
the scene.  FreeCAD's own headlight stays on, so the intensities are modest.
"""
import FreeCAD

from CoinLights import directional_light
from Utils import view_utils
import create_scene_config

WARM = (1.0, 0.95, 0.86)
COOL = (0.84, 0.90, 1.0)
WHITE = (1.0, 1.0, 1.0)


def _view_axes(doc):
    """(forward, right, up) of the first 3D view of ``doc``; isometric if there is none."""
    forward = FreeCAD.Vector(-1, 1, -1)
    up = FreeCAD.Vector(0, 0, 1)
    view = view_utils.first_view(doc)
    if view is not None:
        try:
            forward = FreeCAD.Vector(view.getViewDirection())
            up = view.getCameraOrientation().multVec(FreeCAD.Vector(0, 1, 0))
        except Exception:
            pass
    forward.normalize()
    right = forward.cross(up)
    if right.Length < 1e-6:
        right = FreeCAD.Vector(1, 0, 0)
    right.normalize()
    up = right.cross(forward).normalize()
    return forward, right, up


def _from(source, min_height=None):
    """Direction of a light coming from ``source`` (a vector pointing at the light)."""
    source = FreeCAD.Vector(source)
    source.normalize()
    if min_height is not None and source.z < min_height:
        # shadows are cast on the ground: the light has to come from above
        source.z = min_height
        source.normalize()
    return source.negative()


def _light(doc, group, name, direction, intensity, color, shadows):
    obj = directional_light.createDirectionalLight(doc, name)
    obj.Direction = direction
    obj.Intensity = intensity
    obj.Color = color
    obj.CastShadows = shadows
    directional_light.placeGizmo(obj)
    group.addObject(obj)
    return obj


def _group(doc, name):
    group = doc.addObject("App::DocumentObjectGroup", name)
    create_scene_config.getSceneFolder(doc, create=True).addObject(group)
    return group


def createThreePoint(doc):
    """Key light (casts the shadows), a weaker fill from the other side, a rim from behind."""
    forward, right, up = _view_axes(doc)
    group = _group(doc, "ThreePointLights")
    back = forward.negative()
    _light(doc, group, "KeyLight", _from(back * 0.5 + up * 0.7 - right * 0.7, 0.35),
           0.45, WARM, True)
    _light(doc, group, "FillLight", _from(back * 0.6 + right * 0.8 + up * 0.15),
           0.15, COOL, False)
    _light(doc, group, "RimLight", _from(forward * 0.8 + up * 0.6 + right * 0.3),
           0.25, WHITE, False)
    return group


def createStudio(doc):
    """A soft light from above and two side lights: even, product-photo lighting."""
    forward, right, up = _view_axes(doc)
    group = _group(doc, "StudioLights")
    back = forward.negative()
    _light(doc, group, "TopLight", _from(FreeCAD.Vector(0.15, -0.1, 1)), 0.3, WHITE, True)
    _light(doc, group, "LeftLight", _from(back * 0.6 - right * 0.9 + up * 0.3), 0.15, WHITE, False)
    _light(doc, group, "RightLight", _from(back * 0.6 + right * 0.9 + up * 0.3), 0.15, WHITE, False)
    return group


def createSun(doc):
    """One directional light set by compass direction and height (Azimuth, Elevation)."""
    obj = directional_light.createDirectionalLight(doc, "Sun")
    obj.Azimuth = 135.0
    obj.Elevation = 45.0
    obj.Intensity = 0.5
    obj.Color = WARM
    obj.CastShadows = True
    directional_light.placeGizmo(obj)
    return obj
