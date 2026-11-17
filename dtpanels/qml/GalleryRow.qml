// SPDX-License-Identifier: LGPL-2.1-or-later
// Copyright (c) 2025-2026 OficineRobotica
// Image gallery: one tile per option ({name, label, url}), the current one highlighted,
// plus a "browse" tile. The value is the option name (a file path).
import QtQuick

Item {
    id: row
    property var p
    property var th
    property string value: { var v = bridge.values[p.name]; return v === undefined ? "" : v }
    property int columns: 3
    property real tile: Math.floor((width - (columns - 1) * Math.round(6 * th.s)) / columns)
    implicitHeight: grid.implicitHeight + Math.round(8 * th.s)
    width: parent ? parent.width : 0

    Flow {
        id: grid
        y: Math.round(4 * th.s)
        width: parent.width
        spacing: Math.round(6 * th.s)
        Repeater {
            model: bridge.galleries[p.name] || []
            Rectangle {
                property bool sel: modelData.name === row.value
                width: row.tile; height: row.tile + Math.round(18 * th.s)
                radius: Math.round(6 * th.s)
                color: sel ? th.accent : th.field
                Image {
                    x: 3; y: 3
                    width: parent.width - 6; height: row.tile - 6
                    source: modelData.url
                    sourceSize.width: 128; sourceSize.height: 128
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    visible: modelData.url !== ""
                }
                Rectangle {         // "None": no image
                    x: 3; y: 3
                    width: parent.width - 6; height: row.tile - 6
                    radius: Math.round(4 * th.s)
                    visible: modelData.url === ""
                    color: th.card
                    border.width: 1; border.color: th.line
                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width * 0.9; height: Math.max(1, Math.round(1.5 * th.s))
                        rotation: -40
                        color: th.muted
                    }
                }
                Text {
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: Math.round(3 * th.s)
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    text: modelData.label
                    color: parent.sel ? th.accentText : th.text
                    font.pixelSize: Math.round(10 * th.s); font.family: th.family; font.bold: parent.sel
                    elide: Text.ElideRight
                }
                MouseArea { anchors.fill: parent; onClicked: bridge.setValue(p.name, modelData.name) }
            }
        }
        Rectangle {
            width: row.tile; height: row.tile + Math.round(18 * th.s)
            radius: Math.round(6 * th.s)
            color: "transparent"
            border.width: 1
            border.color: th.line
            Column {
                anchors.centerIn: parent
                spacing: Math.round(2 * th.s)
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "+"; color: th.muted; font.pixelSize: Math.round(26 * th.s); font.family: th.family }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: p.browseLabel; color: th.muted; font.pixelSize: Math.round(10 * th.s); font.family: th.family }
            }
            MouseArea { anchors.fill: parent; onClicked: bridge.trigger("browse:" + p.name) }
        }
    }
}
