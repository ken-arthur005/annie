"""Generate the minimal approved runtime melody package for Training Season.

Run from the repository root:
    audio-lab/.venv/Scripts/python.exe audio-lab/generate_runtime_melody.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/analysis/pitch.pyin-expression-refined.json"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "song_assets/training_season/runtime/melody.json"
DEFAULT_SONG_ID = "training-season-dua-lipa"
REGION_WEIGHTS = {"stable": 1.0, "transition": 0.0, "uncertain": 0.5, "suppressed": 0.0}
EPSILON = 0.000001


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a runtime melody answer key from approved refinement data.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--song-id", default=DEFAULT_SONG_ID)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def runtime_note(source_note: dict[str, Any]) -> dict[str, Any]:
    required = ("id", "start", "end", "pitchMidi", "noteName", "scoringRegions")
    if any(field not in source_note for field in required):
        raise ValueError(f"Source note is missing required runtime fields: {source_note.get('id')!r}")
    return {
        "id": source_note["id"],
        "start": source_note["start"],
        "end": source_note["end"],
        "pitchMidi": source_note["pitchMidi"],
        "noteName": source_note["noteName"],
        "scoringRegions": [
            {
                "start": region["start"],
                "end": region["end"],
                "mode": region["mode"],
                "scoringWeight": region["scoringWeight"],
            }
            for region in source_note["scoringRegions"]
        ],
    }


def build_runtime_melody(source: dict[str, Any], source_path: Path, song_id: str) -> dict[str, Any]:
    if source.get("timeUnit") != "seconds":
        raise ValueError("Approved refinement data must use seconds.")
    notes = source.get("notes")
    if not isinstance(notes, list) or not notes:
        raise ValueError("Approved refinement data must contain notes.")
    return {
        "schemaVersion": 1,
        "purpose": "Approved runtime melody answer key for pitch scoring.",
        "songId": song_id,
        "timeUnit": "seconds",
        "sourcePreparation": {
            "artifact": source_path.relative_to(REPOSITORY_ROOT).as_posix(),
            "artifactSha256": sha256_file(source_path),
            "sourceNotesSha256": source.get("sourceNotesSha256"),
            "sourceContourSha256": source.get("sourceContourSha256"),
        },
        "notes": [runtime_note(note) for note in notes],
    }


def validate_runtime_melody(melody: dict[str, Any]) -> None:
    if melody.get("schemaVersion") != 1 or melody.get("timeUnit") != "seconds":
        raise ValueError("Runtime melody must be schema version 1 and use seconds.")
    if not isinstance(melody.get("songId"), str) or not melody["songId"]:
        raise ValueError("Runtime melody requires a song ID.")
    preparation = melody.get("sourcePreparation")
    if not isinstance(preparation, dict) or not all(isinstance(preparation.get(field), str) and preparation[field] for field in ("artifact", "artifactSha256", "sourceNotesSha256", "sourceContourSha256")):
        raise ValueError("Runtime melody requires complete source preparation traceability.")

    notes = melody.get("notes")
    if not isinstance(notes, list) or not notes:
        raise ValueError("Runtime melody must contain at least one note.")
    seen_ids: set[str] = set()
    previous_end = -math.inf
    for note in notes:
        identifier = note.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in seen_ids:
            raise ValueError(f"Runtime note has an invalid or duplicate ID: {identifier!r}")
        seen_ids.add(identifier)
        start, end, pitch = note.get("start"), note.get("end"), note.get("pitchMidi")
        if not all(finite_number(value) for value in (start, end, pitch)) or start >= end:
            raise ValueError(f"Runtime note {identifier} has invalid timing or pitch.")
        if start < previous_end - EPSILON:
            raise ValueError(f"Runtime note {identifier} overlaps the previous note.")
        previous_end = end
        if not isinstance(note.get("noteName"), str) or not note["noteName"]:
            raise ValueError(f"Runtime note {identifier} lacks a note name.")
        regions = note.get("scoringRegions")
        if not isinstance(regions, list) or not regions:
            raise ValueError(f"Runtime note {identifier} lacks scoring regions.")
        cursor = start
        for region in regions:
            region_start, region_end = region.get("start"), region.get("end")
            mode, weight = region.get("mode"), region.get("scoringWeight")
            if not all(finite_number(value) for value in (region_start, region_end, weight)) or region_start >= region_end:
                raise ValueError(f"Runtime note {identifier} has an invalid scoring region.")
            if mode not in REGION_WEIGHTS or abs(weight - REGION_WEIGHTS[mode]) > EPSILON:
                raise ValueError(f"Runtime note {identifier} has an invalid scoring mode or weight.")
            if abs(region_start - cursor) > EPSILON or region_end > end + EPSILON:
                raise ValueError(f"Runtime note {identifier} has non-contiguous scoring regions.")
            cursor = region_end
        if abs(cursor - end) > EPSILON:
            raise ValueError(f"Runtime note {identifier} scoring regions do not cover the full note.")


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Approved refinement data does not exist: {input_path}")
    source = json.loads(input_path.read_text(encoding="utf-8"))
    melody = build_runtime_melody(source, input_path, args.song_id)
    validate_runtime_melody(melody)
    output_path.write_text(json.dumps(melody, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote runtime melody to {output_path}")
    print(f"Validated {len(melody['notes'])} runtime notes.")


if __name__ == "__main__":
    main()
