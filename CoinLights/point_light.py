# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
import FreeCAD
from pivy import coin

import CoinLights.universal_light as light
from Utils.resource_utils import iconPath


class PointLight(light.UniversalLight):
    type = 'PointLight'

    def setProperties(self, obj):
        super().setProperties(obj)
        if 'Location' not in obj.PropertiesList:
            obj.addProperty("App::PropertyVector", "Location", "Light",
                            "The position of the light in the scene").Location = FreeCAD.Vector(0, -1, 0)


class ViewProviderPointLight(light.ViewProviderUniversalLight):
    def createLightInstance(self):
        return coin.SoPointLight()

    def getIcon(self):
        return iconPath("CreatePointLight.svg")


def createPointLight(doc=None):
    doc = doc or FreeCAD.ActiveDocument
    center, size = light.sceneExtent(doc)
    obj = doc.addObject("App::FeaturePython", "PointLight")
    PointLight(obj)
    if size > 0:
        # above the scene, towards the viewer of the default isometric view
        obj.Location = center + FreeCAD.Vector(0.5, -0.5, 0.8) * size
    if FreeCAD.GuiUp:
        ViewProviderPointLight(obj.ViewObject)
    light.addToScene(obj)
    return obj


if __name__ == "__main__":
    createPointLight()
