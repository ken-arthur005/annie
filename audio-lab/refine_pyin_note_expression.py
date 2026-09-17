"""Add conservative expression-tolerance metadata to segmented expected notes.

Run from the repository root:
    audio-lab/.venv/Scripts/python.exe audio-lab/refine_pyin_note_expression.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NOTES_INPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-notes.json"
DEFAULT_CONTOUR_INPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-smoothed.json"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-expression-refined.json"
DEFAULT_REVIEW_OUTPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-expression-refined.review.json"
DEFAULT_PLOT_OUTPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-expression-refinement-overview.svg"
USABLE_STATUSES = {"detected", "interpolated"}


@dataclass(frozen=True)
class RefinementConfig:
    minimum_transition_cents: float = 75.0
    maximum_transition_duration_ms: float = 250.0
    maximum_transition_note_fraction: float = 0.35
    minimum_transition_frames_per_note: int = 4
    minimum_transition_mean_confidence: float = 0.2
    minimum_monotonicity: float = 0.7
    maximum_transition_frame_step_cents: float = 60.0
    maximum_overshoot_duration_ms: float = 150.0
    maximum_overshoot_target_distance_cents: float = 35.0
    uncertain_mean_confidence: float = 0.1
    uncertain_low_confidence_fraction: float = 0.5
    uncertain_scoring_weight: float = 0.5


def parse_args() -> argparse.Namespace:
    defaults = RefinementConfig()
    parser = argparse.ArgumentParser(description="Refine expected-note scoring regions for expression tolerance.")
    parser.add_argument("--notes-input", type=Path, default=DEFAULT_NOTES_INPUT)
    parser.add_argument("--contour-input", type=Path, default=DEFAULT_CONTOUR_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review-output", type=Path, default=DEFAULT_REVIEW_OUTPUT)
    parser.add_argument("--plot-output", type=Path, default=DEFAULT_PLOT_OUTPUT)
    parser.add_argument("--maximum-transition-duration-ms", type=float, default=defaults.maximum_transition_duration_ms)
    parser.add_argument("--maximum-overshoot-duration-ms", type=float, default=defaults.maximum_overshoot_duration_ms)
    return parser.parse_args()


def config_from_args(args: argparse.Namespace) -> RefinementConfig:
    config = RefinementConfig(
        maximum_transition_duration_ms=args.maximum_transition_duration_ms,
        maximum_overshoot_duration_ms=args.maximum_overshoot_duration_ms,
    )
    if config.maximum_transition_duration_ms <= 0 or config.maximum_overshoot_duration_ms <= 0:
        raise ValueError("Maximum durations must be positive.")
    if not 0 < config.maximum_transition_note_fraction < 0.5:
        raise ValueError("Maximum transition note fraction must be between zero and 0.5.")
    if not 0 <= config.minimum_transition_mean_confidence <= 1:
        raise ValueError("Transition confidence must be within [0, 1].")
    return config


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_inputs(notes_document: dict[str, Any], contour_document: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if notes_document.get("timeUnit") != "seconds" or contour_document.get("timeUnit") != "seconds":
        raise ValueError("Both inputs must use seconds as their time unit.")
    notes = notes_document.get("notes")
    frames = contour_document.get("frames")
    if not isinstance(notes, list) or not notes or not isinstance(frames, list) or not frames:
        raise ValueError("Both inputs must contain non-empty notes or frames.")
    previous_end = -math.inf
    for index, note in enumerate(notes):
        required = ("id", "start", "end", "pitchMidi", "frameStartIndex", "frameEndIndexExclusive")
        if any(field not in note for field in required):
            raise ValueError(f"Note {index} is missing required segmentation fields.")
        if not note["start"] < note["end"] or note["start"] < previous_end - 0.000001:
            raise ValueError(f"Note {note['id']} has invalid or overlapping timings.")
        if not 0 <= note["frameStartIndex"] < note["frameEndIndexExclusive"] <= len(frames):
            raise ValueError(f"Note {note['id']} has invalid frame indices.")
        previous_end = note["end"]
    for index, frame in enumerate(frames):
        if not isinstance(frame.get("time"), (int, float)) or not math.isfinite(frame["time"]):
            raise ValueError(f"Frame {index} has an invalid time.")
        if frame.get("status") in USABLE_STATUSES and not isinstance(frame.get("smoothedPitchMidi"), (int, float)):
            raise ValueError(f"Usable frame {index} lacks a smoothed pitch.")
    return notes, frames


def cents_distance(first: float, second: float) -> float:
    return abs(first - second) * 100


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def usable_pitch_frames(frames: list[dict[str, Any]], start: int, end: int) -> list[dict[str, Any]]:
    return [
        frame for frame in frames[start:end]
        if frame.get("status") in USABLE_STATUSES and isinstance(frame.get("smoothedPitchMidi"), (int, float))
    ]


def monotonicity(pitches: list[float], direction: float) -> float:
    changes = [direction * (current - previous) for previous, current in zip(pitches, pitches[1:])]
    total = sum(abs(change) for change in changes)
    return sum(changes) / total if total else 0.0


def transition_for_pair(
    previous: dict[str, Any], current: dict[str, Any], frames: list[dict[str, Any]], config: RefinementConfig
) -> dict[str, Any] | None:
    pitch_difference = current["pitchMidi"] - previous["pitchMidi"]
    if cents_distance(current["pitchMidi"], previous["pitchMidi"]) < config.minimum_transition_cents:
        return None
    if previous["frameEndIndexExclusive"] != current["frameStartIndex"]:
        return None

    maximum_total_seconds = config.maximum_transition_duration_ms / 1000
    previous_duration = previous["end"] - previous["start"]
    current_duration = current["end"] - current["start"]
    previous_seconds = min(maximum_total_seconds / 2, previous_duration * config.maximum_transition_note_fraction)
    current_seconds = min(maximum_total_seconds / 2, current_duration * config.maximum_transition_note_fraction)
    previous_start = max(previous["frameStartIndex"], next(
        (index for index in range(previous["frameEndIndexExclusive"] - 1, previous["frameStartIndex"] - 1, -1)
         if frames[index]["time"] < previous["end"] - previous_seconds),
        previous["frameStartIndex"],
    ))
    current_end = min(current["frameEndIndexExclusive"], next(
        (index + 1 for index in range(current["frameStartIndex"], current["frameEndIndexExclusive"])
         if frames[index]["time"] >= current["start"] + current_seconds),
        current["frameEndIndexExclusive"],
    ))
    transition_frames = usable_pitch_frames(frames, previous_start, current_end)
    previous_count = sum(frame["time"] < previous["end"] for frame in transition_frames)
    current_count = len(transition_frames) - previous_count
    confidences = [float(frame.get("confidence", 0.0)) for frame in transition_frames]
    pitches = [float(frame["smoothedPitchMidi"]) for frame in transition_frames]
    direction = 1.0 if pitch_difference > 0 else -1.0
    frame_steps_cents = [abs(current - previous) * 100 for previous, current in zip(pitches, pitches[1:])]
    if (
        previous_count < config.minimum_transition_frames_per_note
        or current_count < config.minimum_transition_frames_per_note
        or mean(confidences) < config.minimum_transition_mean_confidence
        or monotonicity(pitches, direction) < config.minimum_monotonicity
        or max(frame_steps_cents, default=0.0) > config.maximum_transition_frame_step_cents
    ):
        return None
    observed_change = direction * (pitches[-1] - pitches[0]) * 100
    if observed_change < config.minimum_transition_cents:
        return None
    return {
        "previousNoteId": previous["id"],
        "nextNoteId": current["id"],
        "start": round(frames[previous_start]["time"], 6),
        "end": round(frames[current_end - 1]["time"], 6),
        "reason": "monotonicPitchChange",
        "meanConfidence": round(mean(confidences), 6),
        "monotonicity": round(monotonicity(pitches, direction), 4),
        "observedChangeCents": round(observed_change, 4),
    }


def longest_target_dwell_frames(note: dict[str, Any], frames: list[dict[str, Any]], config: RefinementConfig) -> int:
    longest = current = 0
    for frame in usable_pitch_frames(frames, note["frameStartIndex"], note["frameEndIndexExclusive"]):
        if cents_distance(float(frame["smoothedPitchMidi"]), note["pitchMidi"]) <= config.maximum_overshoot_target_distance_cents:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def is_short_returning_overshoot(
    previous: dict[str, Any], note: dict[str, Any], following: dict[str, Any], frames: list[dict[str, Any]], transition_pairs: set[tuple[str, str]], config: RefinementConfig
) -> bool:
    duration_ms = (note["end"] - note["start"]) * 1000
    return (
        duration_ms <= config.maximum_overshoot_duration_ms
        and previous["pitchMidi"] == following["pitchMidi"]
        and cents_distance(note["representativePitchMidi"], previous["pitchMidi"])
        > config.maximum_overshoot_target_distance_cents
        and note["meanConfidence"] >= config.minimum_transition_mean_confidence
        and (previous["id"], note["id"]) in transition_pairs
        and (note["id"], following["id"]) in transition_pairs
        and longest_target_dwell_frames(note, frames, config) < config.minimum_transition_frames_per_note
    )


def regions_for_note(note: dict[str, Any], transitions: list[dict[str, Any]], mode: str, weight: float) -> list[dict[str, Any]]:
    if mode != "stable":
        return [{"start": note["start"], "end": note["end"], "mode": mode, "scoringWeight": weight}]
    regions: list[dict[str, Any]] = []
    cursor = note["start"]
    for transition in transitions:
        start = max(note["start"], transition["start"])
        end = min(note["end"], transition["end"])
        if cursor < start:
            regions.append({"start": round(cursor, 6), "end": round(start, 6), "mode": "stable", "scoringWeight": 1.0})
        if start < end:
            regions.append({"start": round(start, 6), "end": round(end, 6), "mode": "transition", "scoringWeight": 0.0})
        cursor = max(cursor, end)
    if cursor < note["end"]:
        regions.append({"start": round(cursor, 6), "end": note["end"], "mode": "stable", "scoringWeight": 1.0})
    return regions


def refine_notes(notes: list[dict[str, Any]], frames: list[dict[str, Any]], config: RefinementConfig) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    transitions = [
        transition for previous, current in zip(notes, notes[1:])
        if (transition := transition_for_pair(previous, current, frames, config)) is not None
    ]
    transition_pairs = {(transition["previousNoteId"], transition["nextNoteId"]) for transition in transitions}
    suppressed_ids = {
        note["id"] for previous, note, following in zip(notes, notes[1:], notes[2:])
        if is_short_returning_overshoot(previous, note, following, frames, transition_pairs, config)
    }
    transition_by_note: dict[str, list[dict[str, Any]]] = {note["id"]: [] for note in notes}
    for transition in transitions:
        transition_by_note[transition["previousNoteId"]].append(transition)
        transition_by_note[transition["nextNoteId"]].append(transition)

    refined: list[dict[str, Any]] = []
    uncertain_ids: list[str] = []
    for note in notes:
        output = dict(note)
        if note["id"] in suppressed_ids:
            mode, weight, reason = "suppressed", 0.0, "shortReturnToNeighboringTarget"
        elif (
            note["meanConfidence"] < config.uncertain_mean_confidence
            or note["lowConfidenceFrameFraction"] >= config.uncertain_low_confidence_fraction
        ):
            mode, weight, reason = "uncertain", config.uncertain_scoring_weight, "lowReferenceConfidence"
            uncertain_ids.append(note["id"])
        else:
            mode, weight, reason = "stable", 1.0, None
        output["scoringMode"] = mode
        output["scoringWeight"] = weight
        output["scoringModeReason"] = reason
        output["scoringRegions"] = regions_for_note(output, transition_by_note[note["id"]], mode, weight)
        refined.append(output)
    review = {
        "transitions": transitions,
        "suppressedOvershootNoteIds": sorted(suppressed_ids),
        "uncertainNoteIds": uncertain_ids,
    }
    return refined, review


def make_summary(notes: list[dict[str, Any]], review: dict[str, Any]) -> dict[str, Any]:
    region_counts = {mode: 0 for mode in ("stable", "transition", "uncertain", "suppressed")}
    for note in notes:
        for region in note["scoringRegions"]:
            region_counts[region["mode"]] += 1
    return {
        "noteCount": len(notes),
        "transitionCount": len(review["transitions"]),
        "suppressedOvershootCount": len(review["suppressedOvershootNoteIds"]),
        "uncertainNoteCount": len(review["uncertainNoteIds"]),
        "scoringRegionCountByMode": region_counts,
    }


def write_overview_svg(frames: list[dict[str, Any]], notes: list[dict[str, Any]], output_path: Path) -> None:
    points = [(frame["time"], frame["smoothedPitchMidi"]) for frame in frames if frame.get("smoothedPitchMidi") is not None]
    minimum = math.floor(min(pitch for _, pitch in points) - 0.5)
    maximum = math.ceil(max(pitch for _, pitch in points) + 0.5)
    duration = frames[-1]["time"]
    x = lambda time: 80 + 1100 * time / duration
    y = lambda pitch: 30 + 400 * (maximum - pitch) / (maximum - minimum)
    path: list[str] = []
    previous_time: float | None = None
    for time, pitch in points:
        path.append(f"{'M' if previous_time is None or time - previous_time > 0.02 else 'L'}{x(time):.2f},{y(pitch):.2f}")
        previous_time = time
    colors = {"stable": "#dc2626", "transition": "#f59e0b", "uncertain": "#7c3aed", "suppressed": "#9ca3af"}
    regions = "".join(
        f'<line x1="{x(region["start"]):.2f}" y1="{y(note["pitchMidi"]):.2f}" x2="{x(region["end"]):.2f}" y2="{y(note["pitchMidi"]):.2f}" stroke="{colors[region["mode"]]}" stroke-width="3"/>'
        for note in notes for region in note["scoringRegions"]
    )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1260" height="500" viewBox="0 0 1260 500">
<style>.label{{font:12px sans-serif;fill:#4b5563}}.title{{font:600 16px sans-serif;fill:#111827}}.legend{{font:13px sans-serif;fill:#374151}}</style>
<rect width="1260" height="500" fill="white"/><text x="80" y="18" class="title">Training Season: expression-tolerant expected notes</text>
<path d="{' '.join(path)}" fill="none" stroke="#2563eb" stroke-width="1" opacity="0.7"/>{regions}
<line x1="80" y1="462" x2="105" y2="462" stroke="#2563eb"/><text x="110" y="467" class="legend">Continuous pitch</text>
<line x1="250" y1="462" x2="275" y2="462" stroke="#dc2626" stroke-width="3"/><text x="280" y="467" class="legend">Stable</text>
<line x1="370" y1="462" x2="395" y2="462" stroke="#f59e0b" stroke-width="3"/><text x="400" y="467" class="legend">Transition</text>
<line x1="510" y1="462" x2="535" y2="462" stroke="#7c3aed" stroke-width="3"/><text x="540" y="467" class="legend">Uncertain</text>
<line x1="650" y1="462" x2="675" y2="462" stroke="#9ca3af" stroke-width="3"/><text x="680" y="467" class="legend">Suppressed</text>
<text x="80" y="490" class="label">0 s</text><text x="1130" y="490" class="label">{duration:.1f} s</text></svg>'''
    output_path.write_text(svg, encoding="utf-8")


def main() -> None:
    args = parse_args()
    config = config_from_args(args)
    notes_path = args.notes_input.resolve()
    contour_path = args.contour_input.resolve()
    if not notes_path.is_file() or not contour_path.is_file():
        raise FileNotFoundError("Both segmented notes and smoothed contour inputs must exist.")
    notes_document = json.loads(notes_path.read_text(encoding="utf-8"))
    contour_document = json.loads(contour_path.read_text(encoding="utf-8"))
    source_notes, frames = validate_inputs(notes_document, contour_document)
    notes, review_details = refine_notes(source_notes, frames, config)
    summary = make_summary(notes, review_details)
    output_path = args.output.resolve()
    review_path = args.review_output.resolve()
    output = {
        "schemaVersion": 1,
        "purpose": "Expression-tolerant expected notes for review; not approved scoring reference data.",
        "generatedAt": datetime.now(UTC).isoformat(),
        "derivedFrom": [notes_path.relative_to(REPOSITORY_ROOT).as_posix(), contour_path.relative_to(REPOSITORY_ROOT).as_posix()],
        "sourceNotesSha256": sha256_file(notes_path),
        "sourceContourSha256": sha256_file(contour_path),
        "sourceAudio": contour_document.get("sourceAudio"),
        "timeUnit": "seconds",
        "configuration": asdict(config),
        "summary": summary,
        "notes": notes,
    }
    review = {
        "schemaVersion": 1,
        "purpose": "Review data for expression-tolerant expected-note refinement.",
        "derivedFrom": output_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "summary": summary,
        **review_details,
    }
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    write_overview_svg(frames, notes, args.plot_output.resolve())
    print(f"Wrote expression-refined notes to {output_path}")
    print(f"Wrote expression refinement review to {review_path}")
    print(f"Wrote expression refinement overview to {args.plot_output.resolve()}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
