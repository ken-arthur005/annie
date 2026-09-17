"""Segment a smoothed continuous pYIN contour into reviewable expected notes.

Run from the repository root:
    audio-lab/.venv/Scripts/python.exe audio-lab/segment_pyin_notes.py
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

from pitch_representation import cents_from_nearest_midi, midi_to_note_name, nearest_midi


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-smoothed.json"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-notes.json"
DEFAULT_REVIEW_OUTPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-notes.review.json"
DEFAULT_PLOT_OUTPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-segmentation-overview.svg"
USABLE_STATUSES = {"detected", "interpolated"}


@dataclass(frozen=True)
class SegmentationConfig:
    change_threshold_cents: float = 75.0
    minimum_candidate_frames: int = 7
    candidate_stability_cents: float = 35.0
    max_bridge_gap_frames: int = 3
    max_bridge_gap_pitch_difference_cents: float = 50.0
    confidence_floor: float = 0.05


@dataclass
class SegmentationResult:
    notes: list[dict[str, Any]]
    ignored_candidates: list[dict[str, Any]]
    bridged_gaps: list[dict[str, Any]]


def parse_args() -> argparse.Namespace:
    defaults = SegmentationConfig()
    parser = argparse.ArgumentParser(
        description="Segment a smoothed pYIN contour into expected note regions."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review-output", type=Path, default=DEFAULT_REVIEW_OUTPUT)
    parser.add_argument("--plot-output", type=Path, default=DEFAULT_PLOT_OUTPUT)
    parser.add_argument("--change-threshold-cents", type=float, default=defaults.change_threshold_cents)
    parser.add_argument("--minimum-candidate-frames", type=int, default=defaults.minimum_candidate_frames)
    parser.add_argument("--candidate-stability-cents", type=float, default=defaults.candidate_stability_cents)
    parser.add_argument("--max-bridge-gap-frames", type=int, default=defaults.max_bridge_gap_frames)
    parser.add_argument("--max-bridge-gap-pitch-difference-cents", type=float, default=defaults.max_bridge_gap_pitch_difference_cents)
    parser.add_argument("--confidence-floor", type=float, default=defaults.confidence_floor)
    return parser.parse_args()


def config_from_args(args: argparse.Namespace) -> SegmentationConfig:
    config = SegmentationConfig(
        change_threshold_cents=args.change_threshold_cents,
        minimum_candidate_frames=args.minimum_candidate_frames,
        candidate_stability_cents=args.candidate_stability_cents,
        max_bridge_gap_frames=args.max_bridge_gap_frames,
        max_bridge_gap_pitch_difference_cents=args.max_bridge_gap_pitch_difference_cents,
        confidence_floor=args.confidence_floor,
    )
    if config.minimum_candidate_frames < 1 or config.max_bridge_gap_frames < 0:
        raise ValueError("Frame-count parameters must be non-negative where applicable.")
    if min(
        config.change_threshold_cents,
        config.candidate_stability_cents,
        config.max_bridge_gap_pitch_difference_cents,
    ) < 0:
        raise ValueError("Pitch-distance parameters must be non-negative.")
    if not 0 <= config.confidence_floor <= 1:
        raise ValueError("Confidence floor must be within [0, 1].")
    return config


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def weighted_median(values: list[float], weights: list[float]) -> float:
    ordered = sorted(zip(values, weights, strict=True), key=lambda item: item[0])
    midpoint = sum(weights) / 2
    cumulative = 0.0
    for value, weight in ordered:
        cumulative += weight
        if cumulative >= midpoint:
            return value
    return ordered[-1][0]


def median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def cents_distance(first_midi: float, second_midi: float) -> float:
    return abs(first_midi - second_midi) * 100


def contiguous_runs(matches: list[bool]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, match in enumerate(matches):
        if match and start is None:
            start = index
        elif not match and start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(matches)))
    return runs


def validate_smoothed_contour(contour: dict[str, Any]) -> list[dict[str, Any]]:
    if contour.get("timeUnit") != "seconds":
        raise ValueError("Smoothed contour must use seconds as its time unit.")
    frames = contour.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("Smoothed contour must contain frames.")
    previous_time = -math.inf
    for index, frame in enumerate(frames):
        timestamp = frame.get("time")
        pitch = frame.get("smoothedPitchMidi")
        status = frame.get("status")
        if not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp) or timestamp <= previous_time:
            raise ValueError(f"Frame {index} has an invalid timestamp.")
        if status in USABLE_STATUSES:
            if not isinstance(pitch, (int, float)) or not math.isfinite(pitch):
                raise ValueError(f"Usable frame {index} lacks a valid smoothed pitch.")
        elif pitch is not None:
            raise ValueError(f"Unavailable frame {index} must not have smoothed pitch.")
        previous_time = timestamp
    return frames


def usable_runs_with_bridged_gaps(
    frames: list[dict[str, Any]], config: SegmentationConfig
) -> tuple[list[list[int]], list[dict[str, Any]]]:
    usable = [frame["status"] in USABLE_STATUSES for frame in frames]
    base_runs = [list(range(start, end)) for start, end in contiguous_runs(usable)]
    if not base_runs:
        return [], []

    joined_runs: list[list[int]] = [base_runs[0]]
    bridged_gaps: list[dict[str, Any]] = []
    for next_run in base_runs[1:]:
        previous_run = joined_runs[-1]
        gap_frames = next_run[0] - previous_run[-1] - 1
        before = frames[previous_run[-1]]["smoothedPitchMidi"]
        after = frames[next_run[0]]["smoothedPitchMidi"]
        if (
            gap_frames <= config.max_bridge_gap_frames
            and cents_distance(before, after) <= config.max_bridge_gap_pitch_difference_cents
        ):
            bridged_gaps.append(
                {
                    "startFrame": previous_run[-1] + 1,
                    "endFrameExclusive": next_run[0],
                    "frameCount": gap_frames,
                    "startTime": frames[previous_run[-1] + 1]["time"],
                    "endTime": frames[next_run[0] - 1]["time"],
                    "pitchDifferenceCents": round(cents_distance(before, after), 4),
                }
            )
            previous_run.extend(next_run)
        else:
            joined_runs.append(next_run)
    return joined_runs, bridged_gaps


def note_from_indices(
    frames: list[dict[str, Any]], indices: list[int], start: float, end: float, start_method: str, end_method: str, config: SegmentationConfig, note_id: str
) -> dict[str, Any]:
    pitches = [frames[index]["smoothedPitchMidi"] for index in indices]
    confidences = [frames[index]["confidence"] for index in indices]
    representative = weighted_median(pitches, [max(value, config.confidence_floor) for value in confidences])
    expected_midi = nearest_midi(representative)
    hop = frames[1]["time"] - frames[0]["time"]
    voiced_coverage = min(1.0, len(indices) * hop / max(end - start, hop))
    return {
        "id": note_id,
        "start": round(start, 6),
        "end": round(end, 6),
        "pitchMidi": expected_midi,
        "noteName": midi_to_note_name(expected_midi),
        "representativePitchMidi": round(representative, 6),
        "representativeCentsOffset": round(cents_from_nearest_midi(representative, expected_midi), 4),
        "frameStartIndex": indices[0],
        "frameEndIndexExclusive": indices[-1] + 1,
        "voicedFrameCount": len(indices),
        "interpolatedFrameCount": sum(frames[index]["status"] == "interpolated" for index in indices),
        "voicedCoverage": round(voiced_coverage, 4),
        "meanConfidence": round(sum(confidences) / len(confidences), 6),
        "medianConfidence": round(median(confidences), 6),
        "lowConfidenceFrameFraction": round(
            sum(value < 0.1 for value in confidences) / len(confidences), 4
        ),
        "startBoundaryMethod": start_method,
        "endBoundaryMethod": end_method,
    }


def segment_run(
    frames: list[dict[str, Any]], indices: list[int], config: SegmentationConfig, note_number: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    if not indices:
        return [], [], note_number
    hop = frames[1]["time"] - frames[0]["time"]
    notes: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    current_start = 0
    candidate_start: int | None = None
    position = 1

    while position < len(indices):
        active_indices = indices[current_start : candidate_start if candidate_start is not None else position]
        active_pitch = median([frames[index]["smoothedPitchMidi"] for index in active_indices])
        current_pitch = frames[indices[position]]["smoothedPitchMidi"]

        if candidate_start is None:
            if (
                cents_distance(current_pitch, active_pitch) >= config.change_threshold_cents
                and nearest_midi(current_pitch) != nearest_midi(active_pitch)
            ):
                candidate_start = position
            position += 1
            continue

        candidate_indices = indices[candidate_start : position + 1]
        candidate_pitches = [frames[index]["smoothedPitchMidi"] for index in candidate_indices]
        if cents_distance(current_pitch, active_pitch) < config.change_threshold_cents / 2:
            ignored.append(
                {
                    "startTime": frames[indices[candidate_start]]["time"],
                    "endTime": frames[indices[position]]["time"],
                    "frameCount": len(candidate_indices),
                    "reason": "returnedToActivePitch",
                }
            )
            candidate_start = None
            position += 1
            continue

        recent = candidate_pitches[-config.minimum_candidate_frames :]
        candidate_pitch = median(recent)
        candidate_spread = median([abs(value - candidate_pitch) * 100 for value in recent])
        if (
            len(candidate_indices) >= config.minimum_candidate_frames
            and nearest_midi(candidate_pitch) != nearest_midi(active_pitch)
            and cents_distance(candidate_pitch, active_pitch) >= config.change_threshold_cents
            and candidate_spread <= config.candidate_stability_cents
        ):
            old_target = nearest_midi(active_pitch)
            new_target = nearest_midi(candidate_pitch)
            crossing = next(
                (
                    candidate_start + offset
                    for offset, index in enumerate(indices[candidate_start : position + 1])
                    if abs(frames[index]["smoothedPitchMidi"] - new_target)
                    <= abs(frames[index]["smoothedPitchMidi"] - old_target)
                ),
                candidate_start,
            )
            old_indices = indices[current_start:crossing]
            new_start = crossing
            if len(old_indices) >= config.minimum_candidate_frames:
                start = max(0.0, frames[old_indices[0]]["time"] - hop / 2)
                end = (frames[indices[crossing - 1]]["time"] + frames[indices[crossing]]["time"]) / 2
                notes.append(
                    note_from_indices(
                        frames, old_indices, start, end,
                        "runStart" if current_start == 0 else "midpointCrossing",
                        "midpointCrossing", config, f"note-{note_number:03d}",
                    )
                )
                note_number += 1
            else:
                ignored.append(
                    {
                        "startTime": frames[indices[current_start]]["time"],
                        "endTime": frames[indices[crossing - 1]]["time"],
                        "frameCount": len(old_indices),
                        "reason": "shortInitialFragment",
                    }
                )
            current_start = new_start
            candidate_start = None
        position += 1

    final_indices = indices[current_start:]
    if len(final_indices) >= config.minimum_candidate_frames:
        start = max(0.0, frames[final_indices[0]]["time"] - hop / 2)
        if notes:
            start = (frames[indices[current_start - 1]]["time"] + frames[indices[current_start]]["time"]) / 2
        end = frames[final_indices[-1]]["time"] + hop / 2
        notes.append(
            note_from_indices(
                frames, final_indices, start, end,
                "runStart" if current_start == 0 else "midpointCrossing",
                "runEnd", config, f"note-{note_number:03d}",
            )
        )
        note_number += 1
    elif final_indices:
        ignored.append(
            {
                "startTime": frames[final_indices[0]]["time"],
                "endTime": frames[final_indices[-1]]["time"],
                "frameCount": len(final_indices),
                "reason": "shortFinalFragment",
            }
        )
    return notes, ignored, note_number


def segment_frames(frames: list[dict[str, Any]], config: SegmentationConfig) -> SegmentationResult:
    runs, bridged_gaps = usable_runs_with_bridged_gaps(frames, config)
    notes: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    note_number = 1
    for run in runs:
        run_notes, run_ignored, note_number = segment_run(frames, run, config, note_number)
        notes.extend(run_notes)
        ignored.extend(run_ignored)
    return SegmentationResult(notes, ignored, bridged_gaps)


def make_summary(result: SegmentationResult, frames: list[dict[str, Any]]) -> dict[str, Any]:
    durations_ms = [(note["end"] - note["start"]) * 1000 for note in result.notes]
    return {
        "totalFrames": len(frames),
        "noteCount": len(result.notes),
        "ignoredCandidateCount": len(result.ignored_candidates),
        "bridgedGapCount": len(result.bridged_gaps),
        "noteDurationMs": {
            "minimum": round(min(durations_ms), 3) if durations_ms else 0.0,
            "median": round(median(durations_ms), 3) if durations_ms else 0.0,
            "maximum": round(max(durations_ms), 3) if durations_ms else 0.0,
        },
    }


def write_overview_svg(frames: list[dict[str, Any]], notes: list[dict[str, Any]], output_path: Path) -> None:
    points = [(frame["time"], frame["smoothedPitchMidi"]) for frame in frames if frame["smoothedPitchMidi"] is not None]
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
    note_lines = "".join(
        f'<line x1="{x(note["start"]):.2f}" y1="{y(note["pitchMidi"]):.2f}" x2="{x(note["end"]):.2f}" y2="{y(note["pitchMidi"]):.2f}" stroke="#dc2626" stroke-width="3"/>'
        for note in notes
    )
    boundaries = "".join(
        f'<line x1="{x(note["start"]):.2f}" y1="30" x2="{x(note["start"]):.2f}" y2="430" stroke="#fca5a5" stroke-width="1"/>'
        for note in notes[1:]
    )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1260" height="500" viewBox="0 0 1260 500">
<style>.label{{font:12px sans-serif;fill:#4b5563}}.title{{font:600 16px sans-serif;fill:#111827}}.legend{{font:13px sans-serif;fill:#374151}}</style>
<rect width="1260" height="500" fill="white"/><text x="80" y="18" class="title">Training Season: automatic note segmentation overview</text>
<path d="{' '.join(path)}" fill="none" stroke="#2563eb" stroke-width="1" opacity="0.7"/>{boundaries}{note_lines}
<line x1="80" y1="462" x2="105" y2="462" stroke="#2563eb"/><text x="110" y="467" class="legend">Continuous Step 4 pitch</text>
<line x1="270" y1="462" x2="295" y2="462" stroke="#dc2626" stroke-width="3"/><text x="300" y="467" class="legend">Expected note regions</text>
<text x="80" y="490" class="label">0 s</text><text x="1130" y="490" class="label">{duration:.1f} s</text></svg>'''
    output_path.write_text(svg, encoding="utf-8")


def main() -> None:
    args = parse_args()
    config = config_from_args(args)
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    review_output_path = args.review_output.resolve()
    plot_output_path = args.plot_output.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Smoothed contour does not exist: {input_path}")
    contour = json.loads(input_path.read_text(encoding="utf-8"))
    frames = validate_smoothed_contour(contour)
    result = segment_frames(frames, config)
    summary = make_summary(result, frames)
    source_path = input_path.relative_to(REPOSITORY_ROOT).as_posix()
    output = {
        "schemaVersion": 1,
        "purpose": "Automatically segmented expected note regions for review; not approved scoring reference data.",
        "generatedAt": datetime.now(UTC).isoformat(),
        "derivedFrom": source_path,
        "sourceContourSha256": sha256_file(input_path),
        "sourceAudio": contour.get("sourceAudio"),
        "timeUnit": "seconds",
        "configuration": asdict(config),
        "summary": summary,
        "notes": result.notes,
    }
    review = {
        "schemaVersion": 1,
        "purpose": "Review data for automatic expected-note segmentation.",
        "derivedFrom": output_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "summary": summary,
        "ignoredCandidates": result.ignored_candidates,
        "bridgedGaps": result.bridged_gaps,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    review_output_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    write_overview_svg(frames, result.notes, plot_output_path)
    print(f"Wrote note segmentation to {output_path}")
    print(f"Wrote note review to {review_output_path}")
    print(f"Wrote segmentation overview to {plot_output_path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
