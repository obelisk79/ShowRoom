// SPDX-License-Identifier: LGPL-2.1-or-later
// Copyright (c) 2025-2026 OficineRobotica
// A line of explanatory text.
import QtQuick

Item {
    property var p
    property var th
    implicitHeight: note.implicitHeight + Math.round(8 * th.s)
    width: parent ? parent.width : 0
    Text {
        id: note
        y: Math.round(4 * th.s)
        width: parent.width
        text: p.label
        color: th.muted
        wrapMode: Text.WordWrap
        font.pixelSize: Math.round(11 * th.s); font.family: th.family
    }
}
