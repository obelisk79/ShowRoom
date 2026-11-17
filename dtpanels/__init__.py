# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
"""QML task panels of ShowRoom.

Same design and building blocks as the Plastic add-on (gui/panel.py there): a
Python "bridge" exposes a panel model to QML, the QML components draw it in
the colours and font of the running FreeCAD theme, and a Qt Widgets form with
the same content takes over when Qt Quick is not available.
"""
import os

QML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml")
