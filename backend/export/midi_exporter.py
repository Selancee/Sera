"""Minimal MIDI exporter for generated note events."""

from __future__ import annotations

from pathlib import Path


class MidiExporter:
    """Write a type-0 MIDI file without external dependencies."""

    def write_midi(
        self,
        note_events: list[dict[str, object]],
        tempo_bpm: int,
        path: str | Path,
        ticks_per_quarter: int = 480,
    ) -> Path:
        """Write note events to a single-track MIDI file."""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        events: list[tuple[int, int, bytes]] = []
        for note in note_events:
            start = int(float(note["start_quarter"]) * ticks_per_quarter)
            duration = int(float(note["duration_quarter"]) * ticks_per_quarter)
            midi = int(note["midi"])
            velocity = int(note.get("velocity", 76))
            events.append((start, 1, bytes([0x90, midi, velocity])))
            events.append((start + duration, 0, bytes([0x80, midi, 0])))
        events.sort(key=lambda item: (item[0], item[1]))

        track = bytearray()
        microseconds = int(60_000_000 / max(1, tempo_bpm))
        track.extend(self._varlen(0))
        track.extend(b"\xff\x51\x03")
        track.extend(microseconds.to_bytes(3, "big"))
        track.extend(self._varlen(0))
        track.extend(bytes([0xC0, 0]))

        current_tick = 0
        for tick, _, payload in events:
            delta = max(0, tick - current_tick)
            track.extend(self._varlen(delta))
            track.extend(payload)
            current_tick = tick

        track.extend(self._varlen(0))
        track.extend(b"\xff\x2f\x00")
        header = b"MThd" + (6).to_bytes(4, "big") + (0).to_bytes(2, "big") + (1).to_bytes(2, "big")
        header += ticks_per_quarter.to_bytes(2, "big")
        body = b"MTrk" + len(track).to_bytes(4, "big") + bytes(track)
        target.write_bytes(header + body)
        return target

    @staticmethod
    def _varlen(value: int) -> bytes:
        buffer = [value & 0x7F]
        value >>= 7
        while value:
            buffer.insert(0, (value & 0x7F) | 0x80)
            value >>= 7
        return bytes(buffer)
