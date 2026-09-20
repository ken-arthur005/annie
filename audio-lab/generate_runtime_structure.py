"""Generate reviewed shared phrase and section structure for Training Season."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIRECTORY = REPOSITORY_ROOT / "song_assets/training_season/runtime"
DEFAULT_LYRICS = RUNTIME_DIRECTORY / "lyrics.json"
DEFAULT_GUIDE = RUNTIME_DIRECTORY / "structure_guide.md"
DEFAULT_OUTPUT = RUNTIME_DIRECTORY / "structure.json"
SONG_ID = "training-season-dua-lipa"
SONG_DURATION = 209.525011
EPSILON = 0.000001
SECTION_KINDS = {"intro", "verse", "pre-chorus", "chorus", "post-chorus", "bridge", "outro"}

# The guide establishes the musical form. Timed lyric lines establish normal
# phrase boundaries; the three explicit ranges preserve guide boundaries that
# fall inside a merged display line.
SECTION_SPECS: list[dict[str, Any]] = [
    {"id": "section-intro", "kind": "intro", "label": "Intro", "start": 0.0, "end": 8.784, "phrases": []},
    {"id": "section-verse-1", "kind": "verse", "label": "Verse 1", "start": 8.784, "end": 41.825, "phrases": [("line-1",), ("line-2",), ("line-3",), ("line-4",), ("line-5",), ("line-6",), ("line-7",)]},
    {"id": "section-pre-chorus-1", "kind": "pre-chorus", "label": "Pre-Chorus 1", "start": 41.825, "end": 47.278, "phrases": [("line-8",), ("line-9",)]},
    {"id": "section-chorus-1", "kind": "chorus", "label": "Chorus 1", "start": 47.278, "end": 64.43, "phrases": [("line-10",), ("line-11",), ("line-12",), ("line-13",)]},
    {"id": "section-post-chorus-1", "kind": "post-chorus", "label": "Post-Chorus 1", "start": 64.43, "end": 86.701, "phrases": [("line-14",), ("line-15",), ("line-16",), ("line-17",)]},
    {"id": "section-verse-2", "kind": "verse", "label": "Verse 2", "start": 86.701, "end": 115.231, "phrases": [("line-18",), ("line-19",), ("line-20",), ("line-21",), ("line-22",), ("phrase-023", 112.088, 114.911, ("line-23",))]},
    {"id": "section-pre-chorus-2", "kind": "pre-chorus", "label": "Pre-Chorus 2", "start": 115.231, "end": 117.473, "phrases": [("phrase-024", 115.231, 117.213, ("line-23",))]},
    {"id": "section-chorus-2", "kind": "chorus", "label": "Chorus 2", "start": 117.473, "end": 133.046, "phrases": [("line-24",), ("line-25",), ("line-26",), ("line-27",)]},
    {"id": "section-post-chorus-2", "kind": "post-chorus", "label": "Post-Chorus 2", "start": 133.046, "end": 149.89, "phrases": [("line-28",), ("line-29",), ("line-30",), ("line-31",)]},
    {"id": "section-bridge", "kind": "bridge", "label": "Bridge", "start": 149.89, "end": 174.23, "phrases": [("line-32",), ("line-33",), ("line-34",), ("line-35",), ("line-36",), ("line-37",)]},
    {"id": "section-pre-chorus-3", "kind": "pre-chorus", "label": "Pre-Chorus 3", "start": 174.23, "end": 176.192, "phrases": [("line-38",)]},
    {"id": "section-chorus-3", "kind": "chorus", "label": "Chorus 3", "start": 176.192, "end": 189.119, "phrases": [("line-39",), ("line-40",), ("line-41",), ("phrase-043", 187.698, 189.099, ("line-42",))]},
    {"id": "section-outro", "kind": "outro", "label": "Outro", "start": 189.119, "end": SONG_DURATION, "phrases": [("phrase-044", 189.119, 208.296, ("line-42",))]},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate shared runtime phrase and section structure.")
    parser.add_argument("--lyrics", type=Path, default=DEFAULT_LYRICS)
    parser.add_argument("--guide", type=Path, default=DEFAULT_GUIDE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def phrase_from_spec(spec: tuple[Any, ...], line_by_id: dict[str, dict[str, Any]], index: int) -> dict[str, Any]:
    if len(spec) == 1:
        line_id = spec[0]
        line = line_by_id[line_id]
        return {"id": f"phrase-{index:03d}", "start": line["start"], "end": line["end"], "lyricLineIds": [line_id]}
    identifier, start, end, line_ids = spec
    return {"id": identifier, "start": start, "end": end, "lyricLineIds": list(line_ids)}


def build_runtime_structure(lyrics: dict[str, Any], lyrics_path: Path, guide_path: Path) -> dict[str, Any]:
    if lyrics.get("songId") != SONG_ID or lyrics.get("timeUnit") != "seconds":
        raise ValueError("Runtime lyrics must belong to Training Season and use seconds.")
    lines = lyrics.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ValueError("Runtime lyrics must contain timed lines.")
    line_by_id = {line.get("id"): line for line in lines}
    if len(line_by_id) != len(lines) or None in line_by_id:
        raise ValueError("Runtime lyrics require unique line IDs.")

    phrase_index = 1
    sections = []
    for spec in SECTION_SPECS:
        phrases = []
        for phrase_spec in spec["phrases"]:
            phrases.append(phrase_from_spec(phrase_spec, line_by_id, phrase_index))
            phrase_index += 1
        sections.append({key: spec[key] for key in ("id", "kind", "label", "start", "end")} | {"phrases": phrases})

    return {
        "schemaVersion": 1,
        "purpose": "Reviewed shared phrase and section map for scoring and reporting.",
        "songId": SONG_ID,
        "timeUnit": "seconds",
        "songDuration": SONG_DURATION,
        "sourceAssets": {
            "lyrics": {"artifact": lyrics_path.relative_to(REPOSITORY_ROOT).as_posix(), "sha256": sha256_file(lyrics_path)},
            "guide": {"artifact": guide_path.relative_to(REPOSITORY_ROOT).as_posix(), "sha256": sha256_file(guide_path)},
        },
        "sections": sections,
    }


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_runtime_structure(structure: dict[str, Any], lyrics: dict[str, Any]) -> None:
    if structure.get("schemaVersion") != 1 or structure.get("songId") != SONG_ID or structure.get("timeUnit") != "seconds":
        raise ValueError("Runtime structure must be version 1 for Training Season in seconds.")
    duration = structure.get("songDuration")
    if not finite_number(duration) or duration <= 0:
        raise ValueError("Runtime structure requires a positive song duration.")
    lines = lyrics.get("lines", [])
    line_ids = {line.get("id") for line in lines}
    source_assets = structure.get("sourceAssets")
    if not isinstance(source_assets, dict) or not all(
        isinstance(source_assets.get(source), dict)
        and isinstance(source_assets[source].get("artifact"), str)
        and source_assets[source]["artifact"]
        and isinstance(source_assets[source].get("sha256"), str)
        and source_assets[source]["sha256"]
        for source in ("lyrics", "guide")
    ):
        raise ValueError("Runtime structure requires source asset traceability.")
    sections = structure.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("Runtime structure must contain sections.")

    seen_section_ids: set[str] = set()
    seen_phrase_ids: set[str] = set()
    referenced_line_ids: set[str] = set()
    cursor = 0.0
    for section in sections:
        identifier = section.get("id")
        start, end = section.get("start"), section.get("end")
        if not isinstance(identifier, str) or not identifier or identifier in seen_section_ids:
            raise ValueError(f"Invalid or duplicate section ID: {identifier!r}")
        if section.get("kind") not in SECTION_KINDS or not isinstance(section.get("label"), str) or not section["label"]:
            raise ValueError(f"Section {identifier} has an invalid kind or label.")
        if not all(finite_number(value) for value in (start, end)) or start >= end or abs(start - cursor) > EPSILON:
            raise ValueError(f"Section {identifier} does not fit the contiguous song timeline.")
        seen_section_ids.add(identifier)
        cursor = end
        phrases = section.get("phrases")
        if not isinstance(phrases, list):
            raise ValueError(f"Section {identifier} must contain a phrase list.")
        phrase_end = start
        for phrase in phrases:
            phrase_id, phrase_start, phrase_end_value = phrase.get("id"), phrase.get("start"), phrase.get("end")
            linked_lines = phrase.get("lyricLineIds")
            if not isinstance(phrase_id, str) or not phrase_id or phrase_id in seen_phrase_ids:
                raise ValueError(f"Section {identifier} has an invalid or duplicate phrase ID.")
            if not all(finite_number(value) for value in (phrase_start, phrase_end_value)) or phrase_start >= phrase_end_value:
                raise ValueError(f"Phrase {phrase_id} has invalid timing.")
            if phrase_start < phrase_end - EPSILON or phrase_start < start - EPSILON or phrase_end_value > end + EPSILON:
                raise ValueError(f"Phrase {phrase_id} is unordered or outside section {identifier}.")
            if not isinstance(linked_lines, list) or not linked_lines or any(line_id not in line_ids for line_id in linked_lines):
                raise ValueError(f"Phrase {phrase_id} references missing lyric lines.")
            seen_phrase_ids.add(phrase_id)
            referenced_line_ids.update(linked_lines)
            phrase_end = phrase_end_value
    if abs(cursor - duration) > EPSILON:
        raise ValueError("Sections must cover the full song duration.")
    if referenced_line_ids != line_ids:
        raise ValueError("Every timed lyric line must belong to at least one phrase.")


def main() -> None:
    args = parse_args()
    lyrics_path, guide_path, output_path = args.lyrics.resolve(), args.guide.resolve(), args.output.resolve()
    if not lyrics_path.is_file() or not guide_path.is_file():
        raise FileNotFoundError("Runtime lyrics and structure guide must exist.")
    lyrics = json.loads(lyrics_path.read_text(encoding="utf-8"))
    structure = build_runtime_structure(lyrics, lyrics_path, guide_path)
    validate_runtime_structure(structure, lyrics)
    output_path.write_text(json.dumps(structure, indent=2) + "\n", encoding="utf-8")
    phrase_count = sum(len(section["phrases"]) for section in structure["sections"])
    print(f"Wrote runtime structure to {output_path}")
    print(f"Validated {len(structure['sections'])} sections and {phrase_count} phrases.")


if __name__ == "__main__":
    main()
