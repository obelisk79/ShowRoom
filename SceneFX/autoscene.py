# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (c) 2025-2026 OficineRobotica
"""Scene settings for new documents, as chosen in the ShowRoom settings."""
import FreeCAD as App

from Utils import prefs


def apply_defaults(cfg, switches=True):
    """Give a scene configuration the default values (and on/off states)."""
    for prop, key in (('ShadowQuality', 'DefShadowQuality'), ('ShadowDarkness', 'DefShadowDarkness'),
                      ('ShadowSoftness', 'DefShadowSoftness'), ('AOQuality', 'DefAOQuality'),
                      ('AOIntensity', 'DefAOIntensity'), ('WhileNavigating', 'DefWhileNavigating')):
        if prop in cfg.PropertiesList:
            try:
                setattr(cfg, prop, prefs.get(key))
            except Exception:
                pass
    if switches:
        for prop, key in (('Shadows', 'DefShadows'), ('AmbientOcclusion', 'DefAO'),
                          ('ShadowCatcher', 'DefCatcher')):
            if prop in cfg.PropertiesList:
                setattr(cfg, prop, prefs.get(key))


def populate(doc):
    """Scene configuration, starting lights and grid, as in the settings."""
    import create_scene_config
    cfg = create_scene_config.getSceneFolder(doc) or create_scene_config.createSceneFolder(doc)
    rig = prefs.get('StartRig')
    if rig != 'None':
        from CoinLights import rigs
        {'Sun': rigs.createSun, 'Three-point': rigs.createThreePoint,
         'Studio': rigs.createStudio}.get(rig, rigs.createSun)(doc)
    if prefs.get('AutoGrid'):
        from HelperTools import dynamic_grid
        grid = dynamic_grid.createDynamicGrid(doc)
        if grid is not None and 'GroundPlane' in grid.PropertiesList:
            grid.GroundPlane = prefs.get('AutoGroundPlane')
    apply_defaults(cfg)
    doc.recompute()
    return cfg


def _eligible(doc):
    """A document a person is going to work in (not a hidden or temporary one)."""
    if doc is None or getattr(doc, 'Temporary', False):
        return False
    try:
        import FreeCADGui
        return FreeCADGui.getDocument(doc.Name) is not None
    except Exception:
        return False


def _new_document(name):
    doc = App.listDocuments().get(name)
    # opened files have a file name by now; scripts fill theirs right away
    if not _eligible(doc) or doc.FileName or doc.Objects or not prefs.get('AutoScene'):
        return
    populate(doc)
    doc.clearUndos()
    _not_modified(doc)


def _opened_document(name):
    import create_scene_config
    doc = App.listDocuments().get(name)
    if not _eligible(doc) or not prefs.get('AutoSceneOnOpen'):
        return
    if create_scene_config.getSceneFolder(doc) is None:
        populate(doc)


def _not_modified(doc):
    try:
        import FreeCADGui
        FreeCADGui.getDocument(doc.Name).Modified = False
    except Exception:
        pass


class _Observer:
    def slotCreatedDocument(self, doc):
        from PySide import QtCore
        name = doc.Name
        QtCore.QTimer.singleShot(0, lambda: _new_document(name))

    def slotFinishRestoreDocument(self, doc):
        from PySide import QtCore
        name = doc.Name
        QtCore.QTimer.singleShot(0, lambda: _opened_document(name))


_observer = None


def install():
    global _observer
    if _observer is None and App.GuiUp:
        _observer = _Observer()
        App.addDocumentObserver(_observer)
