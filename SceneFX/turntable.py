# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
"""Turntable: the view orbits slowly around the model, effects included.

Meant for presentations and screen recordings.  The camera turns around the
vertical (Z) axis through the center of the model, keeping its height and
tilt.  While it runs the effects are not paused (see navigation.hold).
"""
import math
import time

import FreeCAD
from pivy import coin

from Utils import view_utils
from SceneFX import navigation

DEFAULT_PERIOD = 15.0       # seconds per turn
INTERVAL_MS = 16

_run = None


class _Run:
    def __init__(self, view, doc):
        from PySide import QtCore
        import FreeCADGui
        self.view = view
        self.doc_name = doc.Name
        box = view_utils.scene_bound_box(view, doc)
        if box is None:
            self.center = coin.SbVec3f(0, 0, 0)
        else:
            self.center = coin.SbVec3f((box[0] + box[3]) / 2, (box[1] + box[4]) / 2,
                                       (box[2] + box[5]) / 2)
        self.last = time.time()
        self.timer = QtCore.QTimer(FreeCADGui.getMainWindow())
        self.timer.setInterval(INTERVAL_MS)
        self.timer.timeout.connect(self.tick)
        navigation.hold(True)
        self.timer.start()

    def period(self):
        import create_scene_config
        try:
            doc = FreeCAD.listDocuments().get(self.doc_name)
            cfg = create_scene_config.getSceneFolder(doc) if doc is not None else None
            return float(getattr(cfg, 'TurntablePeriod', DEFAULT_PERIOD))
        except Exception:
            return DEFAULT_PERIOD

    def tick(self):
        now = time.time()
        elapsed, self.last = min(now - self.last, 0.25), now
        try:
            if self.doc_name not in FreeCAD.listDocuments():
                raise RuntimeError("document closed")
            camera = self.view.getCameraNode()
            period = self.period()
            if abs(period) < 0.1:
                return
            turn = coin.SbRotation(coin.SbVec3f(0, 0, 1), 2.0 * math.pi * elapsed / period)
            offset = turn.multVec(camera.position.getValue() - self.center)
            camera.position = self.center + offset
            camera.orientation = camera.orientation.getValue() * turn
        except Exception:
            stop()      # the view or its document is gone

    def end(self):
        self.timer.stop()
        navigation.hold(False)


def is_running():
    return _run is not None


def start(view, doc):
    global _run
    stop()
    _run = _Run(view, doc)


def stop():
    global _run
    if _run is not None:
        run, _run = _run, None
        run.end()


def toggle(view, doc):
    if is_running():
        stop()
        return False
    start(view, doc)
    return True
