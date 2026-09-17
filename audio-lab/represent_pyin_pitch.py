"""Add continuous musical pitch representations to a filtered pYIN contour.

This stage does not smooth the contour or segment it into notes. Nearest-note
fields are descriptive only; pitchMidi remains a continuous value.

Run from the repository root:
    audio-lab/.venv/Scripts/python.exe audio-lab/represent_pyin_pitch.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pitch_representation import (
    REFERENCE_A4_HZ,
    REFERENCE_A4_MIDI,
    cents_from_nearest_midi,
    hz_to_continuous_midi,
    midi_to_note_name,
    nearest_midi,
)


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-filtered.json"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-musical.json"
VALID_STATUSES = {"detected", "interpolated", "unavailable", "rejected"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add continuous MIDI, nearest note, and cents to a filtered pYIN contour."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_filtered_contour(contour: dict[str, Any]) -> list[dict[str, Any]]:
    if contour.get("timeUnit") != "seconds":
        raise ValueError("Filtered contour must use seconds as its time unit.")
    frames = contour.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("Filtered contour must contain at least one frame.")

    previous_time = -math.inf
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            raise ValueError(f"Frame {index} is not an object.")
        timestamp = frame.get("time")
        frequency = frame.get("frequencyHz")
        status = frame.get("status")
        if not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp):
            raise ValueError(f"Frame {index} has an invalid timestamp.")
        if timestamp <= previous_time:
            raise ValueError("Filtered contour timestamps must be strictly increasing.")
        if status not in VALID_STATUSES:
            raise ValueError(f"Frame {index} has an unsupported status: {status!r}.")
        if frequency is None:
            if status not in {"unavailable", "rejected"}:
                raise ValueError(f"Frame {index} has no frequency but is not unavailable or rejected.")
        elif (
            not isinstance(frequency, (int, float))
            or isinstance(frequency, bool)
            or not math.isfinite(frequency)
            or frequency <= 0
        ):
            raise ValueError(f"Frame {index} has an invalid frequency.")
        previous_time = timestamp
    return frames


def musical_frame(frame: dict[str, Any]) -> dict[str, Any]:
    frequency = frame["frequencyHz"]
    if frequency is None:
        pitch_midi: float | None = None
        nearest_note_midi: int | None = None
        nearest_note_name: str | None = None
        cents_from_nearest_note: float | None = None
    else:
        continuous_midi = hz_to_continuous_midi(float(frequency))
        nearest_note_midi = nearest_midi(continuous_midi)
        pitch_midi = round(continuous_midi, 6)
        nearest_note_name = midi_to_note_name(nearest_note_midi)
        cents_from_nearest_note = round(
            cents_from_nearest_midi(continuous_midi, nearest_note_midi), 4
        )

    return {
        "time": frame["time"],
        "frequencyHz": frequency,
        "pitchMidi": pitch_midi,
        "nearestMidi": nearest_note_midi,
        "nearestNoteName": nearest_note_name,
        "centsFromNearestNote": cents_from_nearest_note,
        "detectorVoiced": frame["detectorVoiced"],
        "voicedProbability": frame["voicedProbability"],
        "confidence": frame["confidence"],
        "confidenceClass": frame["confidenceClass"],
        "status": frame["status"],
        "reasons": frame["reasons"],
    }


def make_summary(frames: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "totalFrames": len(frames),
        "musicalPitchFrames": sum(frame["pitchMidi"] is not None for frame in frames),
        "detectedFrames": sum(frame["status"] == "detected" for frame in frames),
        "interpolatedFrames": sum(frame["status"] == "interpolated" for frame in frames),
        "unavailableFrames": sum(frame["status"] == "unavailable" for frame in frames),
        "rejectedFrames": sum(frame["status"] == "rejected" for frame in frames),
    }


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Filtered contour does not exist: {input_path}")

    contour = json.loads(input_path.read_text(encoding="utf-8"))
    raw_frames = validate_filtered_contour(contour)
    frames = [musical_frame(frame) for frame in raw_frames]
    source_path = input_path.relative_to(REPOSITORY_ROOT).as_posix()
    output = {
        "schemaVersion": 1,
        "purpose": "Continuous musical-pitch representation derived from the filtered pYIN contour; not approved scoring reference data.",
        "generatedAt": datetime.now(UTC).isoformat(),
        "derivedFrom": source_path,
        "sourceContourSha256": sha256_file(input_path),
        "sourceAudio": contour.get("sourceAudio"),
        "timeUnit": "seconds",
        "configuration": {
            "referenceA4Hz": REFERENCE_A4_HZ,
            "referenceA4Midi": REFERENCE_A4_MIDI,
            "temperament": "12-TET",
            "noteNaming": "sharp",
            "pitchMidiDecimalPlaces": 6,
            "centsDecimalPlaces": 4,
        },
        "summary": make_summary(frames),
        "frames": frames,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote continuous musical contour to {output_path}")
    print(json.dumps(output["summary"], indent=2))


if __name__ == "__main__":
    main()
