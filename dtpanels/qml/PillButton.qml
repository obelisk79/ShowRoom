// SPDX-License-Identifier: LGPL-2.1-or-later
// Copyright (c) 2025-2026 OficineRobotica
import QtQuick

Rectangle {
    id: btn
    property var th
    property string label
    property bool primary: false
    property bool active: false
    signal clicked()
    width: txt.implicitWidth + Math.round(22 * th.s)
    height: Math.round(26 * th.s)
    radius: Math.round(4 * th.s)
    color: active || (primary && !m.pressed) ? th.accent : (m.pressed ? th.line : th.field)
    border.width: active ? 0 : (primary ? 0 : 1)
    border.color: th.line
    Text {
        id: txt
        anchors.centerIn: parent
        text: btn.label
        color: btn.active || btn.primary ? btn.th.accentText : btn.th.text
        font.pixelSize: Math.round(12 * th.s); font.family: th.family
        font.bold: btn.primary || btn.active
    }
    MouseArea { id: m; anchors.fill: parent; onClicked: btn.clicked() }
}
