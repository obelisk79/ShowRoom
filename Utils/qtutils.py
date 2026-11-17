# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
"""Small Qt helpers.

FreeCAD ships a ``PySide`` shim that maps to the Qt binding the running build
really uses (PySide6 on FreeCAD 26.x, PySide2 on old Qt5 builds), so this is
the only import that works everywhere.  With Qt6 the widgets live in
``QtWidgets`` only, the old ``PySide.QtGui`` alias for widgets is gone.
"""
from PySide import QtCore, QtGui, QtWidgets  # noqa: F401

import FreeCADGui

# File patterns
IMAGE_FILES = "Image Files (*.png *.jpg *.bmp *.tif)"
JSON_FILES = "JSON Files (*.json)"


def mainWindow():
    return FreeCADGui.getMainWindow()


def activeWindow():
    return QtWidgets.QApplication.activeWindow() or mainWindow()


def showInfo(title, message):
    QtWidgets.QMessageBox.information(activeWindow(), title, message)


def userSelectedFile(title, filePattern, mustExist=True):
    if mustExist:
        fileName = QtWidgets.QFileDialog.getOpenFileName(activeWindow(), title, '', filePattern)[0]
    else:
        fileName = QtWidgets.QFileDialog.getSaveFileName(activeWindow(), title, '', filePattern)[0]
    return fileName or None
