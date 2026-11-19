# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
"""The gizmo of one light: Coin nodes added to the light's view provider.

What it draws (all driven by the light's properties):

* every light: an icon ("badge") at the light, constant size, over the model;
* selected point and spot lights: red / green / blue arrows to move the light
  along X, Y, Z and a square to move it horizontally, constant size;
* spot light: the light cone (translucent, hidden by the model like a real
  object), the axis, the ring where the cone meets the target, a target grip
  (drag it onto the model: the light follows) and a grip on the ring for the
  cone angle;
* point light: a dashed line down to the bottom of the model, to read height;
* sun (directional light): its icon over the model on the side it comes
  from, a compass on the ground (N E S W), a grip on the compass for the
  azimuth and an arc with a grip for the elevation.

The gizmo itself cannot be picked by FreeCAD: interaction.py does its own hit
testing on the positions published in ``self.grips``.
"""
import math

import FreeCAD
from pivy import coin

from Gizmos import images
from Utils import view_utils

ARROW_PX = 78           # length of the move arrows on screen
AXES = (('x', (1, 0, 0), (0.90, 0.28, 0.30)),
        ('y', (0, 1, 0), (0.18, 0.62, 0.37)),
        ('z', (0, 0, 1), (0.24, 0.48, 0.98)))
WARM = (0.95, 0.65, 0.17)
INK = (0.12, 0.14, 0.19)
SLATE = (0.36, 0.39, 0.44)


def V(p):
    return FreeCAD.Vector(p[0], p[1], p[2])


def scene_extent(doc):
    """(centre, lowest z, horizontal radius) of the model, without lights and grids."""
    view = view_utils.first_view(doc)
    box = view_utils.scene_bound_box(view, doc) if view is not None else None
    if box is None:
        return FreeCAD.Vector(0, 0, 0), 0.0, 50.0
    center = FreeCAD.Vector((box[0] + box[3]) / 2, (box[1] + box[4]) / 2, (box[2] + box[5]) / 2)
    radius = 0.5 * math.hypot(box[3] - box[0], box[4] - box[1])
    return center, box[2], max(radius, 5.0)


def perpendiculars(axis):
    axis = V(axis)
    if axis.Length < 1e-9:
        axis = FreeCAD.Vector(0, 0, -1)
    axis.normalize()
    ref = FreeCAD.Vector(0, 0, 1) if abs(axis.z) < 0.95 else FreeCAD.Vector(1, 0, 0)
    a = axis.cross(ref)
    a.normalize()
    b = axis.cross(a)
    b.normalize()
    return axis, a, b


# ---------------------------------------------------------------- node helpers
def _lines(color, width=2.0, pattern=0xFFFF, closed=False):
    """Group drawing a polyline; returns (group, coordinates node, line set node)."""
    group = coin.SoSeparator()
    material = coin.SoBaseColor()
    material.rgb = color
    style = coin.SoDrawStyle()
    style.lineWidth = width
    style.linePattern = pattern
    coords = coin.SoCoordinate3()
    lines = coin.SoLineSet()
    for node in (material, style, coords, lines):
        group.addChild(node)
    group.closed = closed
    return group, coords, lines


def _set_line(coords, lines, points, closed=False):
    points = [tuple(p) for p in points]
    if closed and points:
        points.append(points[0])
    coords.point.setNum(0)
    if points:
        coords.point.setValues(0, len(points), points)
    lines.numVertices.setValues(0, 1, [len(points)]) if points else lines.numVertices.setNum(0)


def _image_at(kind_fn, *args, **kw):
    group = coin.SoSeparator()
    tr = coin.SoTranslation()
    image = images.make(kind_fn, *args, **kw)
    group.addChild(tr)
    group.addChild(image)
    return group, tr, image


def _arrows():
    """Unit-length move handles; scaled so that 1 unit = ARROW_PX pixels."""
    group = coin.SoSeparator()
    style = coin.SoDrawStyle()
    style.lineWidth = 3.5
    group.addChild(style)
    light_model = coin.SoLightModel()
    light_model.model = coin.SoLightModel.BASE_COLOR
    group.addChild(light_model)
    for name, axis, color in AXES:
        arm = coin.SoSeparator()
        material = coin.SoBaseColor()
        material.rgb = color
        arm.addChild(material)
        coords = coin.SoCoordinate3()
        coords.point.setValues(0, 2, [tuple(0.3 * c for c in axis), tuple(0.84 * c for c in axis)])
        arm.addChild(coords)
        line = coin.SoLineSet()
        line.numVertices.setValue(2)
        arm.addChild(line)
        head = coin.SoSeparator()
        tf = coin.SoTransform()
        tf.translation = tuple(0.92 * c for c in axis)
        tf.rotation.setValue(coin.SbRotation(coin.SbVec3f(0, 1, 0), coin.SbVec3f(*axis)))
        head.addChild(tf)
        cone = coin.SoCone()
        cone.bottomRadius = 0.07
        cone.height = 0.18
        head.addChild(cone)
        arm.addChild(head)
        group.addChild(arm)
    # square to move on the XY (ground) plane
    plane = coin.SoSeparator()
    material = coin.SoMaterial()
    material.diffuseColor = AXES[2][2]
    material.transparency = 0.55
    plane.addChild(material)
    hints = coin.SoShapeHints()
    hints.shapeType = coin.SoShapeHints.UNKNOWN_SHAPE_TYPE
    plane.addChild(hints)
    coords = coin.SoCoordinate3()
    coords.point.setValues(0, 4, [(0.36, 0.36, 0), (0.58, 0.36, 0), (0.58, 0.58, 0), (0.36, 0.58, 0)])
    plane.addChild(coords)
    face = coin.SoFaceSet()
    face.numVertices.setValue(4)
    plane.addChild(face)
    group.addChild(plane)
    return group


# ---------------------------------------------------------------------- gizmo
class LightGizmo:
    def __init__(self, vp):
        self.vp = vp
        self.obj = vp.Object
        # when a file is opened the view provider is attached before the light's
        # Proxy is restored: take the kind from the view provider's class then
        self.kind = getattr(getattr(self.obj, 'Proxy', None), 'type', None) or \
            type(vp).__name__.replace('ViewProvider', '')
        self.selected = False
        self.hover = None
        self.grips = {}             # name -> 3D point, for hit testing
        self.arrow_scale = 1.0      # world units per arrow unit (set from the camera)
        self.extent = (FreeCAD.Vector(0, 0, 0), 0.0, 50.0)

        self.root = coin.SoSwitch()             # ShowManipulator
        self.root.whichChild = coin.SO_SWITCH_ALL
        body = coin.SoSeparator()
        self.root.addChild(body)
        pick = coin.SoPickStyle()
        pick.style = coin.SoPickStyle.UNPICKABLE
        body.addChild(pick)
        # With real-time shadows on, Coin's shadow shader would draw the gizmo
        # too, with wrong colours: an empty shader program switches it off here.
        body.addChild(coin.SoShaderProgram())
        no_shadow = view_utils.new_node('SoShadowStyle')
        if no_shadow is not None:
            view_utils.set_field(no_shadow, 'style', 'NO_SHADOWING')
            body.addChild(no_shadow)

        # depth tested: the cone of a spot light, hidden by the model
        self.cone_sw = coin.SoSwitch()
        body.addChild(self.cone_sw)
        if self.kind == 'SpotLight':
            cone = coin.SoSeparator()
            unlit = coin.SoLightModel()             # a flat warm glow: lit, it turns grey-blue
            unlit.model = coin.SoLightModel.BASE_COLOR
            cone.addChild(unlit)
            material = coin.SoMaterial()
            material.diffuseColor = (1.0, 0.80, 0.42)
            material.transparency = 0.8
            cone.addChild(material)
            hints = coin.SoShapeHints()
            hints.shapeType = coin.SoShapeHints.UNKNOWN_SHAPE_TYPE
            cone.addChild(hints)
            self.cone_tf = coin.SoTransform()
            cone.addChild(self.cone_tf)
            self.cone = coin.SoCone()
            self.cone.parts = coin.SoCone.SIDES
            cone.addChild(self.cone)
            self.cone_sw.addChild(cone)

        # always on top
        top = coin.SoAnnotation()
        body.addChild(top)
        self.sel_sw = coin.SoSwitch()
        top.addChild(self.sel_sw)
        handles = coin.SoSeparator()
        self.sel_sw.addChild(handles)
        self._build_handles(handles)

        self.drag_sw = coin.SoSwitch()
        top.addChild(self.drag_sw)
        drag = coin.SoSeparator()
        self.drag_sw.addChild(drag)
        self.ghost_sw = coin.SoSwitch()
        drag.addChild(self.ghost_sw)
        group, self.ghost_tr, self.ghost = _image_at(images.badge, self.kind, 'ghost')
        self.ghost_sw.addChild(group)
        group, self.chip_tr, self.chip = _image_at(images.label, ' ', pad_left=30)
        self.chip.horAlignment = coin.SoImage.LEFT
        self.chip.vertAlignment = coin.SoImage.BOTTOM
        drag.addChild(group)

        group, self.badge_tr, self.badge = _image_at(images.badge, self.kind, 'idle')
        top.addChild(group)

    # ---------------------------------------------------------- building
    def _build_handles(self, parent):
        k = self.kind
        if k in ('PointLight', 'SpotLight'):
            if k == 'SpotLight':
                g, self.axis_c, self.axis_l = _lines(INK, 2.0, 0xF0F0)
                parent.addChild(g)
                g, self.ring_c, self.ring_l = _lines(WARM, 2.0, 0xFF00)
                parent.addChild(g)
                g, self.target_tr, self.target_img = _image_at(images.handle, images.ACCENT, dot=images.ACCENT)
                parent.addChild(g)
                g, self.cone_h_tr, self.cone_h_img = _image_at(images.handle, images.WARM)
                parent.addChild(g)
            else:
                g, self.drop_c, self.drop_l = _lines(INK, 2.0, 0xF0F0)
                parent.addChild(g)
                g, self.foot_c, self.foot_l = _lines(INK, 1.5)
                parent.addChild(g)
            arrows = coin.SoSeparator()
            self.arrows_tr = coin.SoTranslation()
            self.arrows_scale = coin.SoScale()
            arrows.addChild(self.arrows_tr)
            arrows.addChild(self.arrows_scale)
            arrows.addChild(_arrows())
            parent.addChild(arrows)
        else:
            g, self.compass_c, self.compass_l = _lines(SLATE, 1.6, 0xCCCC)
            parent.addChild(g)
            g, self.ticks_c, self.ticks_l = _lines(SLATE, 2.0)
            parent.addChild(g)
            g, self.base_c, self.base_l = _lines(SLATE, 1.6, 0xF0F0)
            parent.addChild(g)
            g, self.arc_c, self.arc_l = _lines(WARM, 3.5)
            parent.addChild(g)
            g, self.ray_c, self.ray_l = _lines(WARM, 2.5, 0xFF00)
            parent.addChild(g)
            self.letters = []
            for letter in 'NESW':
                g, tr, img = _image_at(images.label, letter, dark=False, size=14)
                parent.addChild(g)
                self.letters.append(tr)
            g, self.az_tr, self.az_img = _image_at(images.handle, images.ACCENT)
            parent.addChild(g)
            g, self.el_tr, self.el_img = _image_at(images.handle, images.WARM)
            parent.addChild(g)

    # ------------------------------------------------------------ update
    def target(self):
        o = self.obj
        t = getattr(o, 'Target', None)
        if t is not None:
            return FreeCAD.Vector(t)
        d = FreeCAD.Vector(o.Direction)
        if d.Length < 1e-9:
            d = FreeCAD.Vector(0, 0, -1)
        d.normalize()
        return FreeCAD.Vector(o.Location) + d * 100

    def sun_geometry(self):
        """(centre, radius, ground direction, elevation rad, source direction)."""
        center, zmin, radius = self.extent
        c = FreeCAD.Vector(center.x, center.y, zmin)
        r = radius * 1.15
        az = math.radians(float(self.obj.Azimuth.Value)) if hasattr(self.obj, 'Azimuth') else 0.0
        el = math.radians(float(self.obj.Elevation.Value)) if hasattr(self.obj, 'Elevation') else 45.0
        g = FreeCAD.Vector(math.sin(az), math.cos(az), 0)
        src = g * math.cos(el) + FreeCAD.Vector(0, 0, 1) * math.sin(el)
        return c, r, g, el, src

    def refresh_extent(self):
        try:
            self.extent = scene_extent(self.obj.Document)
        except Exception:
            pass

    def update(self):
        """Put every node where the properties say."""
        o = self.obj
        show = bool(getattr(o, 'ShowManipulator', True))
        self.root.whichChild = coin.SO_SWITCH_ALL if show else coin.SO_SWITCH_NONE
        sel = coin.SO_SWITCH_ALL if self.selected else coin.SO_SWITCH_NONE
        self.sel_sw.whichChild = sel
        self.cone_sw.whichChild = sel
        grips = {}
        if self.kind in ('PointLight', 'SpotLight'):
            L = FreeCAD.Vector(o.Location)
            self.badge_tr.translation = tuple(L)
            self.arrows_tr.translation = tuple(L)
            s = self.arrow_scale
            self.arrows_scale.scaleFactor = (s, s, s)
            grips['badge'] = L
            for name, axis, _ in AXES:
                grips['axis-' + name] = L + V(axis) * (0.92 * s)
            grips['plane'] = L + FreeCAD.Vector(0.47, 0.47, 0) * s
            if self.kind == 'SpotLight':
                T = self.target()
                axis = T - L
                dist = max(axis.Length, 1e-6)
                axis, a, b = perpendiculars(axis)
                angle = math.radians(min(max(float(o.CutOffAngle.Value), 1.0), 89.0))
                r = dist * math.tan(angle)
                self.cone.height = dist
                self.cone.bottomRadius = r
                self.cone_tf.translation = tuple((L + T) * 0.5)
                self.cone_tf.rotation.setValue(coin.SbRotation(coin.SbVec3f(0, 1, 0),
                                                               coin.SbVec3f(*(L - T))))
                _set_line(self.axis_c, self.axis_l, [L, T])
                ring = [T + (a * math.cos(t) + b * math.sin(t)) * r
                        for t in [i * 2 * math.pi / 72 for i in range(72)]]
                _set_line(self.ring_c, self.ring_l, ring, closed=True)
                self.target_tr.translation = tuple(T)
                cone_grip = T + a * r
                self.cone_h_tr.translation = tuple(cone_grip)
                grips['target'] = T
                grips['cone'] = cone_grip
            else:
                center, zmin, radius = self.extent
                foot = FreeCAD.Vector(L.x, L.y, min(zmin, L.z))
                _set_line(self.drop_c, self.drop_l, [L, foot])
                rr = max(radius * 0.08, 1.0)
                _set_line(self.foot_c, self.foot_l,
                          [foot + FreeCAD.Vector(math.cos(t) * rr, math.sin(t) * rr, 0)
                           for t in [i * 2 * math.pi / 36 for i in range(36)]], closed=True)
                grips['foot'] = foot
        else:
            c, r, g, el, src = self.sun_geometry()
            sun = c + src * (r * 1.55)
            self.badge_tr.translation = tuple(sun)
            grips['badge'] = sun
            _set_line(self.compass_c, self.compass_l,
                      [c + FreeCAD.Vector(math.sin(t), math.cos(t), 0) * r
                       for t in [i * 2 * math.pi / 96 for i in range(96)]], closed=True)
            ticks = []
            for i, deg in enumerate((0, 90, 180, 270)):
                d = FreeCAD.Vector(math.sin(math.radians(deg)), math.cos(math.radians(deg)), 0)
                ticks.append((c + d * r, c + d * (r * 1.08)))
                self.letters[i].translation = tuple(c + d * (r * 1.2))
            self.ticks_c.point.setNum(0)
            pts = [tuple(p) for pair in ticks for p in pair]
            self.ticks_c.point.setValues(0, len(pts), pts)
            self.ticks_l.numVertices.setValues(0, 4, [2, 2, 2, 2])
            foot = c + g * r
            _set_line(self.base_c, self.base_l, [c, foot])
            arc = [c + (g * math.cos(e) + FreeCAD.Vector(0, 0, 1) * math.sin(e)) * r
                   for e in [el * i / 40 for i in range(41)]]
            _set_line(self.arc_c, self.arc_l, arc)
            _set_line(self.ray_c, self.ray_l, [sun, c])
            self.az_tr.translation = tuple(foot)
            el_grip = arc[-1]
            self.el_tr.translation = tuple(el_grip)
            grips['azimuth'] = foot
            grips['elevation'] = el_grip
            grips['center'] = c
        self.grips = grips
        self._paint()

    def _paint(self):
        state = 'selected' if self.selected else ('hover' if self.hover == 'badge' else 'idle')
        if getattr(self, '_badge_state', None) != state:
            images.badge(self.badge, self.kind, state)
            self._badge_state = state
        if not self.selected:
            return
        for name, node, color, dot in self._grip_images():
            want = 'hover' if self.hover == name else 'idle'
            key = '_grip_' + name
            if getattr(self, key, None) != want:
                images.handle(node, color, want, dot=dot)
                setattr(self, key, want)

    def _grip_images(self):
        if self.kind == 'SpotLight':
            return [('target', self.target_img, images.ACCENT, images.ACCENT),
                    ('cone', self.cone_h_img, images.WARM, None)]
        if self.kind == 'DirectionalLight':
            return [('azimuth', self.az_img, images.ACCENT, None),
                    ('elevation', self.el_img, images.WARM, None)]
        return []

    # ----------------------------------------------------------- states
    def set_selected(self, on):
        on = bool(on)
        if on != self.selected:
            self.selected = on
            if on:
                self.refresh_extent()
            self.update()

    def set_hover(self, name):
        if name != self.hover:
            self.hover = name
            self._paint()

    def set_arrow_scale(self, world_per_unit):
        if world_per_unit > 0 and abs(world_per_unit - self.arrow_scale) > 1e-6 * world_per_unit:
            self.arrow_scale = world_per_unit
            if self.kind in ('PointLight', 'SpotLight'):
                s = world_per_unit
                self.arrows_scale.scaleFactor = (s, s, s)
                L = FreeCAD.Vector(self.obj.Location)
                for name, axis, _ in AXES:
                    self.grips['axis-' + name] = L + V(axis) * (0.92 * s)
                self.grips['plane'] = L + FreeCAD.Vector(0.47, 0.47, 0) * s

    def show_drag(self, ghost, text, at):
        """While dragging: a ghost icon where the light was (``ghost``, or None)
        and a chip with ``text`` next to the point ``at``."""
        self.ghost_sw.whichChild = coin.SO_SWITCH_NONE if ghost is None else coin.SO_SWITCH_ALL
        if ghost is not None:
            self.ghost_tr.translation = tuple(ghost)
        if at is not None:
            self.chip_tr.translation = tuple(at)
        images.label(self.chip, text, pad_left=30)
        self.drag_sw.whichChild = coin.SO_SWITCH_ALL

    def hide_drag(self):
        self.drag_sw.whichChild = coin.SO_SWITCH_NONE
