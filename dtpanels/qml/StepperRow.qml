// SPDX-License-Identifier: LGPL-2.1-or-later
// Copyright (c) 2025-2026 OficineRobotica
import QtQuick

Item {
    id: row
    property var p
    property var th
    property int value: { var v = bridge.values[p.name]; return v === undefined ? 0 : v }
    implicitHeight: Math.round(34 * th.s)
    width: parent ? parent.width : 0

    Text {
        anchors.left: parent.left
        anchors.right: box.left
        anchors.verticalCenter: parent.verticalCenter
        text: p.label
        color: th.text
        font.pixelSize: Math.round(12 * th.s); font.family: th.family
        elide: Text.ElideRight
    }
    Row {
        id: box
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2
        Repeater {
            model: [-1, 0, 1]
            Rectangle {
                width: Math.round((modelData === 0 ? 36 : 26) * th.s); height: Math.round(24 * th.s)
                radius: Math.round(6 * th.s)
                color: modelData === 0 ? "transparent" : (m.pressed ? th.accent : th.field)
                Text {
                    anchors.centerIn: parent
                    text: modelData === 0 ? row.value : (modelData < 0 ? "−" : "+")
                    color: th.text
                    font.pixelSize: Math.round((modelData === 0 ? 12 : 14) * th.s); font.family: th.family
                    font.bold: modelData === 0
                }
                MouseArea {
                    id: m
                    anchors.fill: parent
                    enabled: modelData !== 0
                    onClicked: bridge.setValue(p.name, Math.max(p.min, Math.min(p.max, row.value + modelData * p.step)))
                }
            }
        }
    }
}
