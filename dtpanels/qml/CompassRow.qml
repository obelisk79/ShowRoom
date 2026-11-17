// SPDX-License-Identifier: LGPL-2.1-or-later
// Copyright (c) 2025-2026 OficineRobotica
// Compass: where the sun comes from. Drag (or click) the dot around the dial.
import QtQuick

Item {
    id: row
    property var p
    property var th
    property real value: { var v = bridge.values[p.name]; return v === undefined ? 0 : v }
    implicitHeight: Math.round(96 * th.s)
    width: parent ? parent.width : 0

    function compassName(a) {
        var names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        return names[Math.round(((a % 360) + 360) % 360 / 45) % 8]
    }

    Rectangle {
        id: dial
        x: 0
        anchors.verticalCenter: parent.verticalCenter
        width: Math.round(86 * th.s); height: width; radius: width / 2
        color: th.field
        border.width: 1
        border.color: th.line
        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.52; height: width; radius: width / 2
            color: "transparent"; border.width: 1; border.color: th.line
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            y: Math.round(3 * th.s)
            text: "N"; color: th.muted
            font.pixelSize: Math.round(10 * th.s); font.family: th.family; font.bold: true
        }
        // the dot: 0° = north (top), clockwise
        Rectangle {
            property real r: dial.width * 0.33
            property real a: row.value * Math.PI / 180
            width: Math.round(13 * th.s); height: width; radius: width / 2
            x: dial.width / 2 + r * Math.sin(a) - width / 2
            y: dial.height / 2 - r * Math.cos(a) - height / 2
            color: "#f2a52b"; border.width: 2; border.color: "white"
        }
        MouseArea {
            anchors.fill: parent
            preventStealing: true
            function pick(mx, my) {
                var dx = mx - width / 2, dy = height / 2 - my
                if (dx * dx + dy * dy < 9) return
                var deg = Math.atan2(dx, dy) * 180 / Math.PI
                bridge.setValue(p.name, Math.round(((deg % 360) + 360) % 360))
            }
            onPressed: function(mouse) { pick(mouse.x, mouse.y) }
            onPositionChanged: function(mouse) { if (pressed) pick(mouse.x, mouse.y) }
        }
    }
    Column {
        anchors.left: dial.right
        anchors.leftMargin: Math.round(12 * th.s)
        anchors.verticalCenter: parent.verticalCenter
        spacing: 1
        Text { text: p.label; color: th.muted; font.pixelSize: Math.round(11 * th.s); font.family: th.family }
        Text { text: Math.round(row.value) + "° " + row.compassName(row.value); color: th.text; font.pixelSize: Math.round(19 * th.s); font.family: th.family; font.bold: true }
        Text { text: "drag the dot"; color: th.muted; font.pixelSize: Math.round(11 * th.s); font.family: th.family }
    }
}
