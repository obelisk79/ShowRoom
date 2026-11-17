// SPDX-License-Identifier: LGPL-2.1-or-later
// Copyright (c) 2025-2026 OficineRobotica
// Floating card shown over the 3D view for the selected light: the essentials,
// with "All options…" for the full task panel. Driven by the same bridge.
import QtQuick

Item {
    id: root
    property var th: bridge.theme
    property real contentHeight: card.height + 16
    onContentHeightChanged: bridge.setContentHeight(contentHeight)
    Component.onCompleted: bridge.setContentHeight(contentHeight)

    // soft shadow
    Rectangle {
        x: card.x - 1; y: card.y + 3
        width: card.width + 2; height: card.height + 4
        radius: card.radius + 2
        color: Qt.rgba(0.08, 0.1, 0.13, 0.16)
    }
    Rectangle {
        id: card
        x: 4; y: 2
        width: root.width - 8
        height: col.implicitHeight + Math.round(24 * th.s)
        radius: Math.round(12 * th.s)
        color: Qt.rgba(Qt.color(th.window).r, Qt.color(th.window).g, Qt.color(th.window).b, 0.96)
        border.width: 1
        border.color: th.line

        Column {
            id: col
            x: Math.round(12 * th.s); y: Math.round(12 * th.s)
            width: parent.width - Math.round(24 * th.s)
            spacing: Math.round(8 * th.s)

            // ---- header
            Item {
                width: parent.width
                height: Math.round(36 * th.s)
                Image {
                    id: icon
                    anchors.verticalCenter: parent.verticalCenter
                    source: bridge.iconUrl
                    width: Math.round(32 * th.s); height: width
                    sourceSize.width: width * 2; sourceSize.height: height * 2
                }
                Column {
                    anchors.left: icon.right
                    anchors.leftMargin: Math.round(10 * th.s)
                    anchors.right: buttons.left
                    anchors.verticalCenter: parent.verticalCenter
                    Text { width: parent.width; text: bridge.title; color: th.text; elide: Text.ElideRight; font.pixelSize: Math.round(15 * th.s); font.family: th.family; font.bold: true }
                    Text { width: parent.width; text: bridge.subtitle; color: th.muted; elide: Text.ElideRight; font.pixelSize: Math.round(11 * th.s); font.family: th.family }
                }
                Row {
                    id: buttons
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    Rectangle {
                        width: Math.round(28 * th.s); height: width; radius: Math.round(7 * th.s)
                        color: bridge.pinned ? th.accent : (pinArea.containsMouse ? th.card : "transparent")
                        Text { anchors.centerIn: parent; text: "⌖"; color: bridge.pinned ? th.accentText : th.muted; font.pixelSize: Math.round(15 * th.s) }
                        MouseArea { id: pinArea; anchors.fill: parent; hoverEnabled: true; onClicked: bridge.togglePin() }
                    }
                    Rectangle {
                        width: Math.round(28 * th.s); height: width; radius: Math.round(7 * th.s)
                        color: closeArea.containsMouse ? th.card : "transparent"
                        Text { anchors.centerIn: parent; text: "✕"; color: th.muted; font.pixelSize: Math.round(13 * th.s) }
                        MouseArea { id: closeArea; anchors.fill: parent; hoverEnabled: true; onClicked: bridge.close() }
                    }
                }
            }

            // ---- parameters
            Repeater {
                model: bridge.sections
                Section { th: root.th; section: modelData; width: col.width }
            }

            // ---- quick actions
            Flow {
                width: parent.width
                spacing: Math.round(6 * th.s)
                visible: bridge.actions.length > 0
                Repeater {
                    model: bridge.actions
                    PillButton {
                        th: root.th
                        label: modelData.label
                        primary: modelData.primary === true
                        active: bridge.activeActions.indexOf(modelData.name) >= 0
                        onClicked: bridge.trigger(modelData.name)
                    }
                }
            }

            // ---- footer
            Item {
                width: parent.width
                height: Math.round(20 * th.s)
                Text {
                    anchors.left: parent.left
                    anchors.right: more.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: bridge.hint; color: th.muted; elide: Text.ElideRight
                    font.pixelSize: Math.round(11 * th.s); font.family: th.family
                }
                Text {
                    id: more
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: "All options…"; color: th.accent
                    font.pixelSize: Math.round(12 * th.s); font.family: th.family; font.bold: true
                    MouseArea { anchors.fill: parent; anchors.margins: -4; cursorShape: Qt.PointingHandCursor; onClicked: bridge.trigger("full") }
                }
            }
        }
    }
}
