# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
"""Hovering, clicking and dragging the light gizmos in the 3D views.

One Qt event filter per 3D view does the hit testing itself, on the
screen projection of the grips the gizmos publish: the gizmo nodes are not
pickable, so FreeCAD's own selection never sees them, and what is under the
pointer is decided here, with comfortable pixel tolerances.

A drag is one undo step ("Move light" ...).  Esc during a drag puts
everything back.  When a task panel is open its own transaction already
covers the edit, so no other transaction is opened.
"""
import math

import FreeCAD
from pivy import coin

from Gizmos import images
from Gizmos.light_gizmo import ARROW_PX
from Utils import view_utils

BADGE_R = 22        # hit radius (logical px) of a light icon
GRIP_R = 14         # of a round grip
ARROW_R = 8         # distance to an arrow
DRAG_START = 4      # px of movement before a press on an icon becomes a drag

_views = {}         # scene graph address -> _ViewHook
_selection = None


def _gizmo(obj):
    try:
        return getattr(obj.ViewObject.Proxy, 'gizmo', None)
    except Exception:
        return None


def lights(doc):
    out = []
    try:
        objects = doc.Objects
    except Exception:
        return out
    for obj in objects:
        if getattr(getattr(obj, 'Proxy', None), 'isDisplayToolsLight', False):
            g = _gizmo(obj)
            if g is not None:
                out.append((obj, g))
    return out


def _visible(obj):
    try:
        return bool(obj.ViewObject.Visibility) and bool(getattr(obj, 'ShowManipulator', True))
    except Exception:
        return False


# ------------------------------------------------------------------- geometry
def _screen(view, p):
    x, y = view.getPointOnViewport(FreeCAD.Vector(p))
    return float(x), float(y)


def _ray(view, x, y):
    """(origin, direction) of the line of sight through viewport pixel x, y."""
    p = FreeCAD.Vector(view.getPoint(int(x), int(y)))
    d = FreeCAD.Vector(view.getViewDirection())
    d.normalize()
    if view.getCameraType() == 'Perspective':
        c = view.getCameraNode().position.getValue()
        origin = FreeCAD.Vector(c[0], c[1], c[2])
        direction = p - origin
        if direction.Length > 1e-12:
            direction.normalize()
            return origin, direction
    return p - d * 1e6, d


def _hit_plane(ray, point, normal):
    origin, direction = ray
    normal = FreeCAD.Vector(normal)
    den = direction.dot(normal)
    if abs(den) < 1e-9:
        return None
    t = (FreeCAD.Vector(point) - origin).dot(normal) / den
    return origin + direction * t


def _closest_on_line(ray, point, axis):
    """Parameter t of the point of the line point + t * axis closest to the ray."""
    o, d = ray
    u = FreeCAD.Vector(axis)
    w = FreeCAD.Vector(point) - o
    a, b, c = u.dot(u), u.dot(d), d.dot(d)
    e, f = u.dot(w), d.dot(w)
    den = a * c - b * b
    if abs(den) < 1e-12:
        return None
    return (b * f - c * e) / den


def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    n = dx * dx + dy * dy
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / n))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def update_arrow_scale(view, gizmo):
    """Make the move arrows ARROW_PX long on screen."""
    if gizmo.kind not in ('PointLight', 'SpotLight') or not gizmo.selected:
        return
    try:
        L = FreeCAD.Vector(gizmo.obj.Location)
        right = view.getCameraOrientation().multVec(FreeCAD.Vector(1, 0, 0))
        a = _screen(view, L)
        b = _screen(view, L + right)
        px = math.hypot(b[0] - a[0], b[1] - a[1])
        if px > 1e-9:
            gizmo.set_arrow_scale(ARROW_PX * images.scale() / px)
    except Exception:
        pass


# --------------------------------------------------------------------- picking
def pick(view, doc, pos):
    """(light, gizmo, grip name) under the viewport position ``pos``, or None."""
    k = images.scale()
    best = None
    items = [(o, g) for o, g in lights(doc) if _visible(o)]
    # grips of the selected lights first: they sit on top of everything
    for obj, g in items:
        if not g.selected:
            continue
        update_arrow_scale(view, g)
        grips = g.grips
        for name in ('target', 'cone', 'azimuth', 'elevation'):
            if name in grips:
                d = math.hypot(*(a - b for a, b in zip(_screen(view, grips[name]), pos)))
                if d <= GRIP_R * k and (best is None or d < best[0]):
                    best = (d, obj, g, name)
        if best is not None:
            return best[1:]
        if 'badge' in grips and g.kind in ('PointLight', 'SpotLight'):
            center = _screen(view, grips['badge'])
            for name in ('axis-x', 'axis-y', 'axis-z'):
                tip = _screen(view, grips[name])
                start = (center[0] + (tip[0] - center[0]) * 0.3, center[1] + (tip[1] - center[1]) * 0.3)
                d = _seg_dist(pos, start, tip)
                if d <= ARROW_R * k and (best is None or d < best[0]):
                    best = (d, obj, g, name)
            sq = _screen(view, grips['plane'])
            d = math.hypot(sq[0] - pos[0], sq[1] - pos[1])
            if d <= 11 * k and (best is None or d < best[0]):
                best = (d, obj, g, 'plane')
        if best is not None:
            return best[1:]
    for obj, g in items:
        if 'badge' not in g.grips:
            continue
        d = math.hypot(*(a - b for a, b in zip(_screen(view, g.grips['badge']), pos)))
        if d <= BADGE_R * k and (best is None or d < best[0]):
            best = (d, obj, g, 'badge')
    return best[1:] if best else None


# ----------------------------------------------------------------------- drags
class _Drag:
    SAVED = ('Location', 'Target', 'Direction', 'CutOffAngle', 'Azimuth', 'Elevation')
    TITLES = {'target': "Aim light", 'cone': "Change light cone", 'azimuth': "Turn sun",
              'elevation': "Raise sun"}

    def __init__(self, view, obj, gizmo, grip, pos):
        self.view, self.obj, self.gizmo, self.grip = view, obj, gizmo, grip
        self.press = pos
        self.started = grip != 'badge'
        self.saved = {n: getattr(obj, n) for n in self.SAVED if hasattr(obj, n)}
        self.txn = False
        self.ray0 = _ray(view, *pos)
        if hasattr(obj, 'Location'):
            self.L0 = FreeCAD.Vector(obj.Location)

    def begin(self):
        import FreeCADGui
        doc = self.obj.Document
        if not FreeCADGui.Control.activeDialog():
            doc.openTransaction(self.TITLES.get(self.grip, "Move light"))
            self.txn = True
        L0 = getattr(self, 'L0', None)
        if self.grip == 'badge' or self.grip.startswith('axis') or self.grip == 'plane':
            n = FreeCAD.Vector(self.view.getViewDirection()) if self.grip != 'plane' else FreeCAD.Vector(0, 0, 1)
            hit = _hit_plane(self.ray0, L0, n)
            self.offset = (L0 - hit) if hit is not None else FreeCAD.Vector()
            self.normal = n
            if self.grip.startswith('axis'):
                self.axis = {'axis-x': FreeCAD.Vector(1, 0, 0), 'axis-y': FreeCAD.Vector(0, 1, 0),
                             'axis-z': FreeCAD.Vector(0, 0, 1)}[self.grip]
                self.t0 = _closest_on_line(self.ray0, L0, self.axis) or 0.0
        self.started = True

    def move(self, pos):
        if not self.started:
            if math.hypot(pos[0] - self.press[0], pos[1] - self.press[1]) < DRAG_START * images.scale():
                return
            if self.gizmo.kind == 'DirectionalLight':
                return              # the sun is moved with its two grips
            self.begin()
        o, g = self.obj, self.gizmo
        ray = _ray(self.view, *pos)
        text = None
        if self.grip in ('badge', 'plane'):
            hit = _hit_plane(ray, self.L0, self.normal)
            if hit is not None:
                o.Location = hit + self.offset
        elif self.grip.startswith('axis'):
            t = _closest_on_line(ray, self.L0, self.axis)
            if t is not None:
                o.Location = self.L0 + self.axis * (t - self.t0)
        elif self.grip == 'target':
            point = self._surface_point(pos)
            if point is None:
                point = _hit_plane(ray, g.target(), FreeCAD.Vector(self.view.getViewDirection()))
            if point is not None and (point - FreeCAD.Vector(o.Location)).Length > 1e-6:
                o.Target = point
            text = "Target"
        elif self.grip == 'cone':
            T = g.target()
            axis = T - FreeCAD.Vector(o.Location)
            dist = axis.Length
            hit = _hit_plane(ray, T, axis)
            if hit is not None and dist > 1e-9:
                angle = math.degrees(math.atan((hit - T).Length / dist))
                o.CutOffAngle = min(max(angle, 1.0), 89.0)
            text = "Cone %d°" % round(o.CutOffAngle.Value)
        elif self.grip in ('azimuth', 'elevation'):
            c, r, gdir, el, src = g.sun_geometry()
            if self.grip == 'azimuth':
                hit = _hit_plane(ray, c, FreeCAD.Vector(0, 0, 1))
                if hit is not None:
                    v = hit - c
                    if math.hypot(v.x, v.y) > 1e-9:
                        o.Azimuth = math.degrees(math.atan2(v.x, v.y)) % 360.0
                text = "Azimuth %d°" % round(o.Azimuth.Value)
            else:
                hit = _hit_plane(ray, c, gdir.cross(FreeCAD.Vector(0, 0, 1)))
                if hit is not None:
                    v = hit - c
                    horizontal = v.dot(gdir)
                    elevation = math.degrees(math.atan2(v.z, horizontal))
                    o.Elevation = min(max(elevation, 0.0), 90.0)
                text = "Elevation %d°" % round(o.Elevation.Value)
        if text is None:
            L = o.Location
            g.show_drag(self.L0, "X %.1f   Y %.1f   Z %.1f" % (L.x, L.y, L.z), L)
        else:
            at = {'target': 'target', 'cone': 'cone', 'azimuth': 'azimuth',
                  'elevation': 'elevation'}[self.grip]
            g.show_drag(None, text, g.grips.get(at))

    def _surface_point(self, pos):
        """Point of the model under the pointer (not of a light or a grid)."""
        from Utils import prefs
        if not prefs.get('SnapTarget'):
            return None
        try:
            info = self.view.getObjectInfo((int(pos[0]), int(pos[1])))
        except Exception:
            info = None
        if not info:
            return None
        doc = self.obj.Document
        hit = doc.getObject(info.get('Object', ''))
        proxy = getattr(hit, 'Proxy', None)
        if getattr(proxy, 'isDisplayToolsLight', False) or getattr(proxy, 'type', None) == 'DynamicGrid':
            return None
        return FreeCAD.Vector(info['x'], info['y'], info['z'])

    def finish(self):
        self.gizmo.hide_drag()
        if self.txn:
            self.obj.Document.commitTransaction()

    def cancel(self):
        self.gizmo.hide_drag()
        if not self.started:
            return
        for name, value in self.saved.items():
            try:
                setattr(self.obj, name, value)
            except Exception:
                pass
        if self.txn:
            self.obj.Document.abortTransaction()


# ----------------------------------------------------------------- view hooks
def _filter_class():
    """Qt event filter on the 3D view's widget.

    It sees the mouse before FreeCAD's navigation style does: a press on a
    grip, the drag that follows and its release never reach the navigation
    (which would otherwise start rotating the view, or swallow the release).
    """
    from PySide import QtCore

    class Filter(QtCore.QObject):
        def __init__(self, hook, parent):
            super().__init__(parent)
            self.hook = hook

        def eventFilter(self, watched, event):
            try:
                return bool(self.hook.qt_event(watched, event))
            except Exception as error:
                FreeCAD.Console.PrintLog("ShowRoom: gizmo event: %s\n" % error)
                return False

    return Filter


class _ViewHook:
    def __init__(self, view, doc):
        self.view = view
        self.doc_name = doc.Name
        self.drag = None
        self.hover = None
        self.camera = None
        self.sensor = coin.SoNodeSensor(self._camera_moved, None)
        widget = view.graphicsView().viewport()
        self.widget = widget
        self.filter = _filter_class()(self, widget)
        widget.installEventFilter(self.filter)
        self.watch_camera()

    def doc(self):
        return FreeCAD.listDocuments().get(self.doc_name)

    def watch_camera(self):
        try:
            camera = self.view.getCameraNode()
        except Exception:
            return
        if not view_utils.same_node(camera, self.camera):
            self.sensor.detach()
            self.camera = camera
            self.sensor.attach(camera)
            self._camera_moved()

    def _camera_moved(self, *args):
        doc = self.doc()
        if doc is None:
            return
        for obj, g in lights(doc):
            if g.selected:
                update_arrow_scale(self.view, g)

    def _set_hover(self, found):
        key = (found[0].Name, found[2]) if found else None
        if key == self.hover:
            return
        doc = self.doc()
        if doc is not None:
            for obj, g in lights(doc):
                g.set_hover(found[2] if found and obj is found[0] else None)
        self.hover = key
        try:
            from PySide import QtCore
            if found is None:
                self.widget.unsetCursor()
            elif found[2] == 'badge':
                self.widget.setCursor(QtCore.Qt.PointingHandCursor)
            else:
                self.widget.setCursor(QtCore.Qt.SizeAllCursor)
        except Exception:
            pass

    def _coin_pos(self, event):
        """Qt widget position -> Coin viewport position (device pixels, y up)."""
        p = event.position() if hasattr(event, 'position') else event.pos()
        ratio = self.widget.devicePixelRatioF()
        return float(p.x()) * ratio, float(self.widget.height() - p.y()) * ratio

    def qt_event(self, watched, event):
        from PySide import QtCore
        t = event.type()
        if t not in (QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseButtonRelease,
                     QtCore.QEvent.MouseMove, QtCore.QEvent.KeyPress, QtCore.QEvent.Leave,
                     QtCore.QEvent.MouseButtonDblClick):
            return False
        doc = self.doc()
        if doc is None:
            return False
        if t == QtCore.QEvent.Leave:
            if self.drag is None:
                self._set_hover(None)
            return False
        if t == QtCore.QEvent.KeyPress:
            if self.drag is not None and event.key() == QtCore.Qt.Key_Escape:
                self.drag.cancel()
                self.drag = None
                return True
            return False
        pos = self._coin_pos(event)
        left = event.button() == QtCore.Qt.LeftButton
        if t in (QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseButtonDblClick) and left:
            if event.modifiers() & (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier | QtCore.Qt.AltModifier):
                return False        # keep FreeCAD's multi-selection and navigation shortcuts
            self.watch_camera()
            found = pick(self.view, doc, pos)
            if found is None:
                return False
            obj, g, grip = found
            select(obj)
            if t == QtCore.QEvent.MouseButtonDblClick:
                from dtpanels import bridge
                bridge.edit(obj)
                return True
            self.drag = _Drag(self.view, obj, g, grip, pos)
            if grip != 'badge':
                self.drag.begin()
            return True
        if t == QtCore.QEvent.MouseButtonRelease and left:
            if self.drag is not None:
                self.drag.finish()
                self.drag = None
                return True
            return False
        if t == QtCore.QEvent.MouseMove:
            if self.drag is not None:
                if not (event.buttons() & QtCore.Qt.LeftButton):
                    self.drag.finish()          # release happened outside of the view
                    self.drag = None
                    return False
                self.drag.move(pos)
                return True
            if event.buttons() == QtCore.Qt.NoButton:
                self._set_hover(pick(self.view, doc, pos))
        return False

    def release(self):
        try:
            self.sensor.detach()
        except Exception:
            pass
        try:
            self.widget.removeEventFilter(self.filter)
        except Exception:
            pass


def select(obj):
    import FreeCADGui
    sel = FreeCADGui.Selection.getSelection(obj.Document.Name)
    if len(sel) == 1 and sel[0] is obj:
        return
    FreeCADGui.Selection.clearSelection()
    FreeCADGui.Selection.addSelection(obj.Document.Name, obj.Name)


def ensure(view, doc):
    """Make ``view`` (showing ``doc``) react to the gizmos."""
    _ensure_selection_observer()
    key = view_utils.node_address(view.getSceneGraph())
    hook = _views.get(key)
    if hook is None:
        _views[key] = _ViewHook(view, doc)
    else:
        hook.watch_camera()


def forget_except(views):
    alive = set()
    for view in views:
        try:
            alive.add(view_utils.node_address(view.getSceneGraph()))
        except Exception:
            pass
    for key in list(_views):
        if key not in alive:
            hook = _views.pop(key)
            hook.release()


def refresh_selection(doc_name=None):
    import FreeCADGui
    documents = FreeCAD.listDocuments()
    names = [doc_name] if doc_name else list(documents)
    for name in names:
        doc = documents.get(name)
        if doc is None:
            continue
        try:
            selected = set(o.Name for o in FreeCADGui.Selection.getSelection(name))
        except Exception:
            selected = set()
        for obj, g in lights(doc):
            was = g.selected
            g.set_selected(obj.Name in selected)
            if g.selected and not was:
                for hook in _views.values():
                    if hook.doc_name == name:
                        update_arrow_scale(hook.view, g)


class _SelectionObserver:
    def addSelection(self, doc, obj, sub, pos):
        refresh_selection(doc)

    def removeSelection(self, doc, obj, sub):
        refresh_selection(doc)

    def setSelection(self, doc):
        refresh_selection(doc)

    def clearSelection(self, doc):
        refresh_selection(doc or None)


def _ensure_selection_observer():
    global _selection
    if _selection is None:
        import FreeCADGui
        _selection = _SelectionObserver()
        FreeCADGui.Selection.addObserver(_selection)


# ------------------------------------------------------------ model extent
# The sun has no position of its own: its icon, compass and arc stand on a
# circle around the model, and the point light's foot sits on the model's
# floor.  Keep that measurement in step with the model, so that the icons
# never move on their own when a light is clicked.
_extent_pending = set()
_extent_timer = None
_extent_observer = None


def _refresh_extents():
    names = list(_extent_pending)
    _extent_pending.clear()
    documents = FreeCAD.listDocuments()
    for name in names:
        doc = documents.get(name)
        if doc is None:
            continue
        for obj, gizmo in lights(doc):
            before = gizmo.extent
            gizmo.refresh_extent()
            if gizmo.extent != before:
                gizmo.update()


def watch_extent(doc):
    """Measure the model of ``doc`` again shortly (after the scene has settled)."""
    global _extent_timer, _extent_observer
    if not FreeCAD.GuiUp or doc is None:
        return
    try:
        _extent_pending.add(doc.Name)
    except Exception:
        return
    if _extent_observer is None:
        _extent_observer = _ExtentObserver()
        FreeCAD.addDocumentObserver(_extent_observer)
    if _extent_timer is None:
        import FreeCADGui
        from PySide import QtCore
        _extent_timer = QtCore.QTimer(FreeCADGui.getMainWindow())
        _extent_timer.setSingleShot(True)
        _extent_timer.setInterval(60)
        _extent_timer.timeout.connect(_refresh_extents)
    _extent_timer.start()


def _has_lights(doc):
    try:
        return any(getattr(getattr(o, 'Proxy', None), 'isDisplayToolsLight', False)
                   for o in doc.Objects)
    except Exception:
        return False


class _ExtentObserver:
    def _touch(self, doc):
        if _has_lights(doc):
            watch_extent(doc)

    def slotRecomputedDocument(self, doc):
        self._touch(doc)

    def slotFinishRestoreDocument(self, doc):
        self._touch(doc)

    def slotUndoDocument(self, doc):
        self._touch(doc)

    def slotRedoDocument(self, doc):
        self._touch(doc)

    def slotDeletedObject(self, obj):
        try:
            self._touch(obj.Document)
        except Exception:
            pass

    def slotChangedObject(self, obj, prop):
        if prop != 'Visibility' or getattr(getattr(obj, 'Proxy', None), 'isDisplayToolsLight', False):
            return
        try:
            self._touch(obj.Document)
        except Exception:
            pass
