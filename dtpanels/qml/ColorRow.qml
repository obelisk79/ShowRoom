// SPDX-License-Identifier: LGPL-2.1-or-later
// Copyright (c) 2025-2026 OficineRobotica
// Colour: preset swatches plus the current colour; clicking it opens the colour dialog.
import QtQuick

Item {
    id: row
    property var p
    property var th
    property string value: { var v = bridge.values[p.name]; return v === undefined ? "#ffffff" : v }
    implicitHeight: Math.round(34 * th.s)
    width: parent ? parent.width : 0

    Text {
        anchors.left: parent.left
        anchors.right: swatches.left
        anchors.rightMargin: Math.round(8 * th.s)
        anchors.verticalCenter: parent.verticalCenter
        text: p.label
        color: th.text
        font.pixelSize: Math.round(12 * th.s); font.family: th.family
        elide: Text.ElideRight
    }
    Row {
        id: swatches
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: Math.round(4 * th.s)
        Repeater {
            model: p.presets
            Rectangle {
                width: Math.round(18 * th.s); height: Math.round(18 * th.s); radius: Math.round(9 * th.s)
                anchors.verticalCenter: parent.verticalCenter
                color: modelData
                border.width: modelData.toLowerCase() === row.value.toLowerCase() ? 2 : 1
                border.color: modelData.toLowerCase() === row.value.toLowerCase() ? th.accent : th.line
                MouseArea { anchors.fill: parent; anchors.margins: -2; onClicked: bridge.setValue(p.name, modelData) }
            }
        }
        Rectangle {
            width: Math.round(46 * th.s); height: Math.round(24 * th.s); radius: Math.round(4 * th.s)
            color: row.value
            border.width: 1
            border.color: th.line
            MouseArea { anchors.fill: parent; onClicked: bridge.pickColor(p.name) }
        }
    }
}
