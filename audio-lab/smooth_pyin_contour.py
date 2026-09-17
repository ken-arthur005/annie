"""Smooth a continuous pYIN musical contour without note segmentation.

Run from the repository root:
    audio-lab/.venv/Scripts/python.exe audio-lab/smooth_pyin_contour.py
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

import numpy as np
from scipy.signal import savgol_filter

from pitch_representation import hz_to_continuous_midi


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-musical.json"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-smoothed.json"
DEFAULT_REVIEW_OUTPUT = (
    REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-smoothed.review.json"
)
DEFAULT_RAW_INPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-raw.json"
DEFAULT_PLOT_OUTPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-smoothing-overview.svg"
USABLE_STATUSES = {"detected", "interpolated"}
VALID_STATUSES = USABLE_STATUSES | {"unavailable", "rejected"}


@dataclass(frozen=True)
class SmoothingConfig:
    window_frames: int = 5
    polynomial_order: int = 2
    transition_guard_cents: float = 100.0


def parse_args() -> argparse.Namespace:
    defaults = SmoothingConfig()
    parser = argparse.ArgumentParser(
        description="Smooth a continuous musical pitch contour without note segmentation."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review-output", type=Path, default=DEFAULT_REVIEW_OUTPUT)
    parser.add_argument("--raw-input", type=Path, default=DEFAULT_RAW_INPUT)
    parser.add_argument("--plot-output", type=Path, default=DEFAULT_PLOT_OUTPUT)
    parser.add_argument("--window-frames", type=int, default=defaults.window_frames)
    parser.add_argument("--polynomial-order", type=int, default=defaults.polynomial_order)
    parser.add_argument("--transition-guard-cents", type=float, default=defaults.transition_guard_cents)
    return parser.parse_args()


def config_from_args(args: argparse.Namespace) -> SmoothingConfig:
    config = SmoothingConfig(
        window_frames=args.window_frames,
        polynomial_order=args.polynomial_order,
        transition_guard_cents=args.transition_guard_cents,
    )
    if config.window_frames < 3 or config.window_frames % 2 == 0:
        raise ValueError("Smoothing window must be an odd number of at least three frames.")
    if not 0 <= config.polynomial_order < config.window_frames:
        raise ValueError("Polynomial order must be non-negative and smaller than the window.")
    if config.transition_guard_cents < 0:
        raise ValueError("Transition guard must be non-negative.")
    return config


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contiguous_runs(matches: list[bool]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, matches_value in enumerate(matches):
        if matches_value and start is None:
            start = index
        elif not matches_value and start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(matches)))
    return runs


def validate_musical_contour(contour: dict[str, Any]) -> list[dict[str, Any]]:
    if contour.get("timeUnit") != "seconds":
        raise ValueError("Musical contour must use seconds as its time unit.")
    frames = contour.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("Musical contour must contain at least one frame.")

    previous_time = -math.inf
    for index, frame in enumerate(frames):
        timestamp = frame.get("time")
        pitch_midi = frame.get("pitchMidi")
        status = frame.get("status")
        if not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp):
            raise ValueError(f"Frame {index} has an invalid timestamp.")
        if timestamp <= previous_time:
            raise ValueError("Musical contour timestamps must be strictly increasing.")
        if status not in VALID_STATUSES:
            raise ValueError(f"Frame {index} has an unsupported status: {status!r}.")
        if pitch_midi is None:
            if status in USABLE_STATUSES:
                raise ValueError(f"Frame {index} is usable but lacks continuous MIDI pitch.")
        elif (
            not isinstance(pitch_midi, (int, float))
            or isinstance(pitch_midi, bool)
            or not math.isfinite(pitch_midi)
        ):
            raise ValueError(f"Frame {index} has an invalid continuous MIDI pitch.")
        previous_time = timestamp
    return frames


def make_output_frame(frame: dict[str, Any], reason: str) -> dict[str, Any]:
    output = dict(frame)
    output["smoothedPitchMidi"] = frame["pitchMidi"]
    output["smoothingApplied"] = False
    output["smoothingReason"] = reason
    return output


def smooth_frames(
    source_frames: list[dict[str, Any]], config: SmoothingConfig
) -> list[dict[str, Any]]:
    """Return copied frames with guarded, centered Savitzky-Golay smoothing."""
    frames = [
        make_output_frame(
            frame,
            "unavailable" if frame["status"] in {"unavailable", "rejected"} else "edgeOfUsableRegion",
        )
        for frame in source_frames
    ]
    usable = [
        frame["status"] in USABLE_STATUSES and frame["pitchMidi"] is not None for frame in source_frames
    ]
    half_window = config.window_frames // 2

    for start, end in contiguous_runs(usable):
        run_length = end - start
        if run_length < config.window_frames:
            for frame in frames[start:end]:
                frame["smoothingReason"] = "shortUsableRegion"
            continue

        original = np.array([source_frames[index]["pitchMidi"] for index in range(start, end)])
        filtered = savgol_filter(original, config.window_frames, config.polynomial_order, mode="interp")
        for offset in range(half_window, run_length - half_window):
            window = original[offset - half_window : offset + half_window + 1]
            if np.max(np.abs(np.diff(window))) * 100 >= config.transition_guard_cents:
                frames[start + offset]["smoothingReason"] = "transitionGuard"
                continue
            frames[start + offset]["smoothedPitchMidi"] = round(float(filtered[offset]), 6)
            frames[start + offset]["smoothingApplied"] = True
            frames[start + offset]["smoothingReason"] = "savgol"
    return frames


def quantiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {"median": 0.0, "p95": 0.0, "maximum": 0.0}
    array = np.array(values)
    return {
        "median": round(float(np.quantile(array, 0.5)), 4),
        "p95": round(float(np.quantile(array, 0.95)), 4),
        "maximum": round(float(np.max(array)), 4),
    }


def make_summary(frames: list[dict[str, Any]]) -> dict[str, Any]:
    reasons = {
        reason: sum(frame["smoothingReason"] == reason for frame in frames)
        for reason in sorted({frame["smoothingReason"] for frame in frames})
    }
    adjustments = [
        abs(frame["smoothedPitchMidi"] - frame["pitchMidi"]) * 100
        for frame in frames
        if frame["smoothingApplied"]
    ]
    return {
        "totalFrames": len(frames),
        "smoothingAppliedFrames": sum(frame["smoothingApplied"] for frame in frames),
        "smoothingReasons": reasons,
        "absoluteAdjustmentCents": quantiles(adjustments),
    }


def group_review_events(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    start: int | None = None
    reason: str | None = None
    for index, frame in enumerate(frames):
        current_reason = frame["smoothingReason"]
        is_event = current_reason != "savgol"
        if start is None:
            if is_event:
                start, reason = index, current_reason
        elif not is_event or current_reason != reason:
            events.append(
                {
                    "startFrame": start,
                    "endFrameExclusive": index,
                    "startTime": frames[start]["time"],
                    "endTime": frames[index - 1]["time"],
                    "frameCount": index - start,
                    "smoothingReason": reason,
                }
            )
            start = index if is_event else None
            reason = current_reason if is_event else None
    if start is not None:
        events.append(
            {
                "startFrame": start,
                "endFrameExclusive": len(frames),
                "startTime": frames[start]["time"],
                "endTime": frames[-1]["time"],
                "frameCount": len(frames) - start,
                "smoothingReason": reason,
            }
        )
    return events


def svg_path(points: list[tuple[float, float]], duration: float, minimum: float, maximum: float) -> str:
    """Render disconnected pitch runs without drawing lines through gaps."""
    if not points:
        return ""
    width, height, left, top = 1100, 400, 80, 30
    hop = 0.01161
    commands: list[str] = []
    previous_time: float | None = None
    for timestamp, pitch in points:
        x = left + width * timestamp / duration
        y = top + height * (maximum - pitch) / (maximum - minimum)
        command = "M" if previous_time is None or timestamp - previous_time > hop * 1.5 else "L"
        commands.append(f"{command}{x:.2f},{y:.2f}")
        previous_time = timestamp
    return " ".join(commands)


def write_overview_svg(
    raw_contour: dict[str, Any], source_frames: list[dict[str, Any]], frames: list[dict[str, Any]], output_path: Path
) -> None:
    raw_points = [
        (frame["time"], hz_to_continuous_midi(frame["frequencyHz"]))
        for frame in raw_contour.get("frames", [])
        if isinstance(frame.get("frequencyHz"), (int, float)) and frame["frequencyHz"] > 0
    ]
    cleaned_points = [
        (frame["time"], frame["pitchMidi"])
        for frame in source_frames
        if frame["pitchMidi"] is not None
    ]
    smoothed_points = [
        (frame["time"], frame["smoothedPitchMidi"])
        for frame in frames
        if frame["smoothedPitchMidi"] is not None
    ]
    all_pitches = [pitch for _, pitch in raw_points + cleaned_points + smoothed_points]
    minimum = math.floor(min(all_pitches) - 0.5)
    maximum = math.ceil(max(all_pitches) + 0.5)
    duration = source_frames[-1]["time"]
    grid = "".join(
        f'<line x1="80" y1="{30 + 400 * index / 6:.2f}" x2="1180" y2="{30 + 400 * index / 6:.2f}" class="grid"/>'
        for index in range(7)
    )
    labels = "".join(
        f'<text x="18" y="{35 + 400 * index / 6:.2f}" class="label">{maximum - (maximum - minimum) * index / 6:.1f}</text>'
        for index in range(7)
    )
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1260" height="500" viewBox="0 0 1260 500">
<style>.grid{{stroke:#d1d5db;stroke-width:1}}.label{{font:12px sans-serif;fill:#4b5563}}.title{{font:600 16px sans-serif;fill:#111827}}.legend{{font:13px sans-serif;fill:#374151}}</style>
<rect width="1260" height="500" fill="white"/>
<text x="80" y="18" class="title">Training Season: continuous pitch contour overview</text>
{grid}{labels}
<path d="{svg_path(raw_points, duration, minimum, maximum)}" fill="none" stroke="#9ca3af" stroke-width="1" opacity="0.5"/>
<path d="{svg_path(cleaned_points, duration, minimum, maximum)}" fill="none" stroke="#2563eb" stroke-width="1.2" opacity="0.65"/>
<path d="{svg_path(smoothed_points, duration, minimum, maximum)}" fill="none" stroke="#dc2626" stroke-width="1.2" opacity="0.8"/>
<line x1="80" y1="462" x2="105" y2="462" stroke="#9ca3af"/><text x="110" y="467" class="legend">Raw pYIN</text>
<line x1="230" y1="462" x2="255" y2="462" stroke="#2563eb"/><text x="260" y="467" class="legend">Step 3 cleaned</text>
<line x1="410" y1="462" x2="435" y2="462" stroke="#dc2626"/><text x="440" y="467" class="legend">Step 4 guarded smoothing</text>
<text x="80" y="490" class="label">0 s</text><text x="1130" y="490" class="label">{duration:.1f} s</text>
</svg>'''
    output_path.write_text(svg, encoding="utf-8")


def main() -> None:
    args = parse_args()
    config = config_from_args(args)
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    review_output_path = args.review_output.resolve()
    raw_input_path = args.raw_input.resolve()
    plot_output_path = args.plot_output.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Musical contour does not exist: {input_path}")
    if not raw_input_path.is_file():
        raise FileNotFoundError(f"Raw contour does not exist: {raw_input_path}")

    contour = json.loads(input_path.read_text(encoding="utf-8"))
    raw_contour = json.loads(raw_input_path.read_text(encoding="utf-8"))
    source_frames = validate_musical_contour(contour)
    frames = smooth_frames(source_frames, config)
    hop_duration_ms = round((source_frames[1]["time"] - source_frames[0]["time"]) * 1000, 6)
    summary = make_summary(frames)
    source_path = input_path.relative_to(REPOSITORY_ROOT).as_posix()
    output = {
        "schemaVersion": 1,
        "purpose": "Guarded smoothing of the continuous reference pitch contour; not approved scoring reference data.",
        "generatedAt": datetime.now(UTC).isoformat(),
        "derivedFrom": source_path,
        "sourceContourSha256": sha256_file(input_path),
        "sourceAudio": contour.get("sourceAudio"),
        "timeUnit": "seconds",
        "configuration": {
            "method": "Savitzky-Golay",
            **asdict(config),
            "hopDurationMs": hop_duration_ms,
            "windowDurationMs": round(config.window_frames * hop_duration_ms, 6),
            "halfWindowDurationMs": round((config.window_frames // 2) * hop_duration_ms, 6),
            "gapPolicy": "split",
        },
        "summary": summary,
        "frames": frames,
    }
    review = {
        "schemaVersion": 1,
        "purpose": "Review events for guarded smoothing of the continuous pYIN contour.",
        "derivedFrom": output_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "summary": summary,
        "events": group_review_events(frames),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    review_output_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    write_overview_svg(raw_contour, source_frames, frames, plot_output_path)
    print(f"Wrote smoothed contour to {output_path}")
    print(f"Wrote smoothing review to {review_output_path}")
    print(f"Wrote smoothing overview to {plot_output_path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
