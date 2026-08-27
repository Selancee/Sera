// Sera MuseScore Studio thin bridge.
// SPDX-License-Identifier: MIT

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import MuseScore 3.0

MuseScore {
    id: root

    version: "0.3.3"
    title: "Sera Score Bridge"
    description: "Send the current score and selection context to Sera, then open a source-preserving MusicXML revision in a separate MuseScore window."
    pluginType: "dialog"
    requiresScore: true
    width: 620
    height: 540

    property string apiBaseUrl: "http://127.0.0.1:8000"
    property string sessionId: ""
    property int latestRevision: 0
    property int openedRevision: 0
    property string sourcePath: ""
    property string statusText: "Ready. Start the Sera desktop app before sending a score."
    property bool busy: false

    function trimTrailingSlash(value) {
        var result = String(value || "")
        while (result.length > 0 && result.charAt(result.length - 1) === "/")
            result = result.slice(0, -1)
        return result
    }

    function safeScoreName() {
        var value = curScore && curScore.scoreName ? String(curScore.scoreName) : "musescore_score"
        value = value.replace(/[^A-Za-z0-9_-]+/g, "_")
        return value.length > 0 ? value.slice(0, 80) : "musescore_score"
    }

    function selectedSourceName() {
        var value = String(sourcePath || "").replace(/\\/g, "/")
        var slash = value.lastIndexOf("/")
        return slash >= 0 ? value.slice(slash + 1) : value
    }

    function measureNumberAtTick(tick, endExclusive) {
        if (!curScore || tick === undefined || tick === null)
            return null
        var measure = curScore.firstMeasure
        var number = 1
        while (measure) {
            var startTick = measure.firstSegment ? measure.firstSegment.tick : 0
            var nextMeasure = measure.nextMeasure
            var nextTick = nextMeasure && nextMeasure.firstSegment ? nextMeasure.firstSegment.tick : Number.MAX_VALUE
            if (endExclusive && number > 1 && tick === startTick)
                return number - 1
            if (tick < nextTick)
                return number
            measure = nextMeasure
            number += 1
        }
        return Math.max(1, curScore.nmeasures || 1)
    }

    function selectionContext() {
        var selection = curScore ? curScore.selection : null
        var context = {
            is_range: false,
            start_measure: null,
            end_measure: null,
            start_tick: null,
            end_tick: null,
            start_staff: null,
            end_staff: null,
            selected_element_count: selection && selection.elements ? selection.elements.length : 0
        }
        if (!selection || !selection.isRange || !selection.startSegment)
            return context

        context.is_range = true
        context.start_tick = selection.startSegment.tick
        context.end_tick = selection.endSegment ? selection.endSegment.tick : null
        context.start_staff = selection.startStaff
        context.end_staff = selection.endStaff
        context.start_measure = measureNumberAtTick(context.start_tick, false)
        context.end_measure = context.end_tick === null
            ? Math.max(1, curScore.nmeasures || 1)
            : measureNumberAtTick(context.end_tick, true)
        return context
    }

    function parseJson(text) {
        if (!String(text || "").trim())
            return { detail: "No response from Sera. Start Sera Desktop, wait for Agent Console, then retry." }
        try {
            return JSON.parse(text)
        } catch (error) {
            return { detail: "Sera returned invalid JSON: " + error }
        }
    }

    function request(method, path, body, callback) {
        var xhr = new XMLHttpRequest()
        xhr.onreadystatechange = function() {
            if (xhr.readyState !== XMLHttpRequest.DONE)
                return
            callback(xhr.status, xhr.responseText, xhr)
        }
        xhr.open(method, trimTrailingSlash(apiBaseUrl) + path)
        xhr.setRequestHeader("Accept", "application/json")
        if (body !== null)
            xhr.setRequestHeader("Content-Type", "application/json")
        xhr.send(body === null ? null : JSON.stringify(body))
    }

    function sendCurrentScore() {
        if (!curScore) {
            statusText = "Open a MuseScore score before running the Sera bridge."
            return
        }
        if (!sourcePath) {
            statusText = "Choose the saved score file first. MuseScore 4.5.2 cannot export through the QML writeScore API."
            return
        }
        busy = true
        statusText = "Converting the saved score through the local MuseScore CLI..."
        var context = selectionContext()
        request("POST", "/integrations/musescore-file-sessions", {
            source_path: sourcePath,
            source_name: selectedSourceName() || safeScoreName() + ".mscz",
            prompt: "Opened from the MuseScore Studio Sera bridge",
            host_context: {
                bridge: "sera_musescore_qml_cli",
                plugin_version: version,
                host_version: mscoreMajorVersion + "." + mscoreMinorVersion + "." + mscoreUpdateVersion,
                score_name: curScore.scoreName || "",
                selection: context
            }
        }, function(status, responseText) {
            busy = false
            var payload = parseJson(responseText)
            if (status < 200 || status >= 300) {
                statusText = "Sera session creation failed (HTTP " + status + "): " + (payload.detail || responseText)
                return
            }
            sessionId = payload.session.session_id
            latestRevision = Number(payload.session.revision || 0)
            openedRevision = 0
            var desktopReady = payload.desktop_delivery && payload.desktop_delivery.desktop_available
            if (!desktopReady) {
                statusText = "The score was saved in Sera, but no desktop window is connected. Start Sera Desktop and send again."
                return
            }
            statusText = context.is_range
                ? "Sent session " + sessionId + " with measures " + context.start_measure + "-" + context.end_measure + ". Generate and apply the proposal in Sera; this bridge opens only the applied host revision."
                : "Sent session " + sessionId + ". Generate and apply the proposal in Sera; this bridge opens only the applied host revision."
        })
    }

    function openLatestReviewedRevision() {
        if (!sessionId) {
            statusText = "Send this score to Sera first."
            return
        }
        busy = true
        statusText = "Checking for a reviewed revision..."
        request("GET", "/integrations/notation-sessions/" + encodeURIComponent(sessionId), null, function(status, responseText) {
            var payload = parseJson(responseText)
            if (status < 200 || status >= 300) {
                busy = false
                statusText = "Could not read the Sera session (HTTP " + status + "): " + (payload.detail || responseText)
                return
            }
            var revision = Number(payload.session.revision || 0)
            if (revision < 1) {
                request(
                    "POST",
                    "/integrations/notation-sessions/" + encodeURIComponent(sessionId) + "/activate",
                    {},
                    function(activateStatus, activateResponse) {
                        busy = false
                        var activatePayload = parseJson(activateResponse)
                        if (activateStatus < 200 || activateStatus >= 300) {
                            statusText = "Session " + sessionId + " has no applied host revision, and Sera could not reactivate it (HTTP " + activateStatus + "): " + (activatePayload.detail || activateResponse)
                            return
                        }
                        var desktopReady = activatePayload.desktop_delivery && activatePayload.desktop_delivery.desktop_available
                        statusText = desktopReady
                            ? "Session " + sessionId + " has no applied host revision yet. Sera Desktop was focused on this exact session. Generate a proposal, click 'Apply and create host revision', then press this button again."
                            : "Session " + sessionId + " has no applied host revision yet. Start Sera Desktop, press this button again, then generate and apply a proposal."
                    }
                )
                return
            }
            if (openedRevision === revision) {
                busy = false
                statusText = "Revision " + revision + " is already open in a separate MuseScore window. Switch to the window whose title ends with _r" + ("0000" + revision).slice(-4) + ".musicxml; the source window intentionally remains unchanged."
                return
            }
            request(
                "POST",
                "/integrations/notation-sessions/" + encodeURIComponent(sessionId) + "/open-in-musescore",
                { revision: revision },
                function(openStatus, openResponse) {
                    busy = false
                    var openPayload = parseJson(openResponse)
                    if (openStatus < 200 || openStatus >= 300) {
                        statusText = "Could not open revision " + revision + " (HTTP " + openStatus + "): " + (openPayload.detail || openResponse)
                        return
                    }
                    latestRevision = revision
                    openedRevision = revision
                    var reviewedPath = String(openPayload.score_path || "").replace(/\\/g, "/")
                    var reviewedName = reviewedPath.slice(reviewedPath.lastIndexOf("/") + 1)
                    statusText = "Opened revision " + revision + " in a separate MuseScore window: " + reviewedName + ". Switch to that window and use Save As to keep it. The original source window is intentionally unchanged."
                }
            )
        })
    }

    FileDialog {
        id: scoreFileDialog
        type: FileDialog.Load
        title: "Choose the saved score currently open in MuseScore"
        onAccepted: {
            root.sourcePath = String(scoreFileDialog.filePath || "")
            scoreFileDialog.visible = false
            root.statusText = root.sourcePath
                ? "Saved score selected. Press Ctrl+S in MuseScore before each send so Sera receives current edits."
                : "No saved score file was selected."
        }
        onRejected: scoreFileDialog.visible = false
        visible: false
    }

    onRun: {
        statusText = "Choose the saved score file, save current edits, then send the score and selection to Sera."
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        Label {
            text: "Sera Score Bridge"
            font.pixelSize: 22
            font.bold: true
        }

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "MuseScore remains the notation source. Version 4.5.2 cannot export from QML, so this bridge sends a user-selected saved score through the local MuseScore CLI; no browser is opened."
        }

        GridLayout {
            columns: 2
            Layout.fillWidth: true
            columnSpacing: 10
            rowSpacing: 8

            Label { text: "Sera API" }
            TextField {
                Layout.fillWidth: true
                text: root.apiBaseUrl
                onEditingFinished: root.apiBaseUrl = text
            }

            Label { text: "Session" }
            TextField {
                Layout.fillWidth: true
                readOnly: true
                text: root.sessionId || "not created"
            }

            Label { text: "Saved score" }
            RowLayout {
                Layout.fillWidth: true
                TextField {
                    Layout.fillWidth: true
                    readOnly: true
                    text: root.sourcePath || "Choose the score file currently open in MuseScore"
                }
                Button {
                    text: "Choose..."
                    enabled: !root.busy
                    onClicked: scoreFileDialog.visible = true
                }
            }
        }

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            font.pixelSize: 11
            text: "Important: save the MuseScore document before sending. Unsaved in-memory edits are not visible to the 4.5.2 plugin API."
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Button {
                Layout.fillWidth: true
                enabled: !root.busy && curScore !== null && root.sourcePath.length > 0
                text: "Send saved score / selection to Sera"
                onClicked: root.sendCurrentScore()
            }

            Button {
                Layout.fillWidth: true
                enabled: !root.busy && root.sessionId.length > 0
                text: root.openedRevision > 0
                    ? "Revision " + root.openedRevision + " opened — switch window"
                    : "Refresh and open applied revision"
                onClicked: root.openLatestReviewedRevision()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"
            border.color: "#777777"
            radius: 4

            Label {
                anchors.fill: parent
                anchors.margins: 12
                wrapMode: Text.WordWrap
                verticalAlignment: Text.AlignTop
                text: root.statusText
            }
        }

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            font.pixelSize: 11
            text: "Safety: this bridge does not write into the open source score. In-place apply and single-step MuseScore undo are reserved for a host-tested follow-up."
        }
    }
}
