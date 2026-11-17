// SPDX-License-Identifier: LGPL-2.1-or-later
// Copyright (c) 2025-2026 OficineRobotica
import QtQuick

Rectangle {
    id: chip
    property var th
    property var item
    property color tone: item.status === "ok" ? th.ok : item.status === "warn" ? th.warn : item.status === "bad" ? th.bad : th.muted
    height: Math.round(44 * th.s)
    radius: Math.round(8 * th.s)
    color: th.field
    Rectangle { x: 0; y: Math.round(8 * th.s); width: 3; height: parent.height - 16; radius: 2; color: chip.tone }
    Column {
        x: Math.round(10 * th.s)
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width - 16
        spacing: 1
        Text { width: parent.width; text: chip.item.label; color: chip.th.muted; font.pixelSize: Math.round(11 * th.s); font.family: th.family; elide: Text.ElideRight }
        Text { width: parent.width; text: chip.item.value; color: chip.item.status === "none" ? chip.th.text : chip.tone; font.pixelSize: Math.round(12 * th.s); font.family: th.family; font.bold: true; elide: Text.ElideRight }
    }
    // utilisation gauge (0..1.5, 1 = limit)
    Rectangle {
        visible: chip.item.gauge >= 0
        anchors.bottom: parent.bottom
        x: Math.round(10 * th.s)
        width: parent.width - 20; height: 2; radius: 1
        color: chip.th.line
        Rectangle { width: parent.width * Math.min(1, chip.item.gauge / 1.5); height: 2; radius: 1; color: chip.tone }
        Rectangle { x: parent.width / 1.5; y: -2; width: 1; height: Math.round(6 * th.s); color: chip.th.text }
    }
}
