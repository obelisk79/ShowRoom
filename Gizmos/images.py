# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
"""Icons and labels of the gizmos, drawn with Qt and shown with SoImage.

SoImage draws a picture at a 3D point, always facing the viewer, at a fixed
size in pixels and over the model (inside an SoAnnotation): exactly what an
icon in the 3D view needs.
"""
import math

from pivy import coin
from PySide import QtCore, QtGui

ACCENT = '#0a6fd6'
WARM = '#f2a52b'
DARK = '#1f2430'
INK = '#ffffff'

_cache = {}


def scale():
    """Device pixels per logical pixel of the screen the main window is on."""
    try:
        import FreeCADGui
        from Utils import prefs
        return max(1.0, float(FreeCADGui.getMainWindow().devicePixelRatioF())) * prefs.gizmo_factor()
    except Exception:
        return 1.0


def _to_coin(image, node):
    """Put a QImage into an SoImage (Coin's rows run bottom to top)."""
    image = image.convertToFormat(QtGui.QImage.Format_RGBA8888).mirrored(False, True)
    w, h = image.width(), image.height()
    data = bytes(image.constBits())[:w * h * 4]
    node.image.setValue(coin.SbVec2s(w, h), 4, data)


def _canvas(size):
    s = scale()
    image = QtGui.QImage(int(math.ceil(size * s)), int(math.ceil(size * s)),
                         QtGui.QImage.Format_RGBA8888)
    image.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.scale(s, s)
    painter.translate(size / 2.0, size / 2.0)
    return image, painter


def _glyph(painter, kind):
    warm = QtGui.QColor(WARM)
    painter.setPen(QtCore.Qt.NoPen)
    if kind == 'SpotLight':
        painter.setBrush(warm)
        painter.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(-6, -7), QtCore.QPointF(6, -7),
                                             QtCore.QPointF(9, 3), QtCore.QPointF(-9, 3)]))
        pen = QtGui.QPen(warm, 2)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        for x0, x1 in ((-5, -8), (0, 0), (5, 8)):
            painter.drawLine(QtCore.QPointF(x0, 7), QtCore.QPointF(x1, 12))
    elif kind == 'DirectionalLight':
        painter.setBrush(warm)
        painter.drawEllipse(QtCore.QPointF(0, 0), 6, 6)
        pen = QtGui.QPen(warm, 2)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        for i in range(8):
            a = i * math.pi / 4
            painter.drawLine(QtCore.QPointF(math.cos(a) * 9, math.sin(a) * 9),
                             QtCore.QPointF(math.cos(a) * 12.5, math.sin(a) * 12.5))
    else:
        painter.setBrush(warm)
        painter.drawEllipse(QtCore.QPointF(0, -3), 7, 7)
        painter.setBrush(QtGui.QColor('#d9d9de'))
        painter.drawRoundedRect(QtCore.QRectF(-4, 4, 8, 5), 1.5, 1.5)
        pen = QtGui.QPen(QtGui.QColor('#d9d9de'), 2)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QtCore.QPointF(-3.5, 11), QtCore.QPointF(3.5, 11))


BADGE = 64      # logical pixels of a badge image (the disk itself is 40)


def badge(node, kind, state):
    """Light icon. state: 'idle', 'hover', 'selected', 'ghost', 'off'."""
    key = ('badge', kind, state, scale())
    image = _cache.get(key)
    if image is None:
        image, p = _canvas(BADGE)
        if state in ('selected', 'hover'):
            p.setPen(QtCore.Qt.NoPen)
            halo = QtGui.QColor(ACCENT)
            halo.setAlphaF(0.16 if state == 'selected' else 0.10)
            p.setBrush(halo)
            p.drawEllipse(QtCore.QPointF(0, 0), 30, 30)
        if state == 'ghost':
            p.setOpacity(0.35)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(DARK if state != 'off' else '#6b7280'))
        p.drawEllipse(QtCore.QPointF(0, 0), 20, 20)
        if state in ('selected', 'hover'):
            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtGui.QPen(QtGui.QColor(ACCENT), 3 if state == 'selected' else 2))
            p.drawEllipse(QtCore.QPointF(0, 0), 24.5, 24.5)
        _glyph(p, kind)
        p.end()
        _cache[key] = image
    _to_coin(image, node)


HANDLE = 32


def handle(node, ring, state='idle', fill='#ffffff', dot=None):
    """Round grip: white disk with a coloured ring (and an optional centre dot)."""
    key = ('handle', ring, state, fill, dot, scale())
    image = _cache.get(key)
    if image is None:
        image, p = _canvas(HANDLE)
        r = 9.5 if state == 'idle' else 11
        if state != 'idle':
            halo = QtGui.QColor(ring)
            halo.setAlphaF(0.22)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(halo)
            p.drawEllipse(QtCore.QPointF(0, 0), 15, 15)
        p.setBrush(QtGui.QColor(fill))
        p.setPen(QtGui.QPen(QtGui.QColor(ring), 3.5))
        p.drawEllipse(QtCore.QPointF(0, 0), r, r)
        if dot:
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(dot))
            p.drawEllipse(QtCore.QPointF(0, 0), 3.5, 3.5)
        p.end()
        _cache[key] = image
    _to_coin(image, node)


def label(node, text, dark=True, size=13, pad_left=0):
    """Rounded label ("chip"): coordinates while dragging, compass letters."""
    key = ('label', text, dark, size, pad_left, scale())
    image = _cache.get(key)
    if image is None:
        s = scale()
        font = QtGui.QFont()
        font.setPixelSize(size)
        font.setWeight(QtGui.QFont.DemiBold)
        metrics = QtGui.QFontMetricsF(font)
        inner = metrics.horizontalAdvance(text) + (20 if dark else 4)
        w = inner + pad_left
        h = metrics.height() + (10 if dark else 2)
        image = QtGui.QImage(int(math.ceil(w * s)), int(math.ceil(h * s)), QtGui.QImage.Format_RGBA8888)
        image.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(image)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing)
        p.scale(s, s)
        if dark:
            bg = QtGui.QColor(DARK)
            bg.setAlphaF(0.92)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(QtCore.QRectF(pad_left, 0, inner, h), 7, 7)
            p.setPen(QtGui.QColor(INK))
        else:
            p.setPen(QtGui.QColor('#3a3f4a'))
        p.setFont(font)
        p.drawText(QtCore.QRectF(pad_left, 0, inner, h), QtCore.Qt.AlignCenter, text)
        p.end()
        if len(_cache) > 400:
            _cache.clear()
        _cache[key] = image
    _to_coin(image, node)


def make(kind_fn, *args, **kw):
    node = coin.SoImage()
    node.vertAlignment = coin.SoImage.HALF
    node.horAlignment = coin.SoImage.CENTER
    kind_fn(node, *args, **kw)
    return node
