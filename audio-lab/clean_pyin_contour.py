"""Conservatively clean a raw pYIN contour without segmenting it into notes.

Run from the repository root:
    audio-lab/.venv/Scripts/python.exe audio-lab/clean_pyin_contour.py
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
DEFAULT_INPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-raw.json"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-filtered.json"
DEFAULT_REVIEW_OUTPUT = (
    REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-filtered.review.json"
)


@dataclass(frozen=True)
class CleaningConfig:
    low_confidence_threshold: float = 0.10
    medium_confidence_threshold: float = 0.30
    max_short_unreliable_region_frames: int = 3
    short_region_max_mean_confidence: float = 0.05
    max_interpolated_gap_frames: int = 2
    max_gap_boundary_difference_cents: float = 75.0
    spike_max_duration_frames: int = 2
    spike_support_frames: int = 2
    spike_support_agreement_cents: float = 100.0
    spike_deviation_cents: float = 200.0
    frequency_boundary_margin_hz: float = 1.0
    interpolation_confidence_scale: float = 0.75


def parse_args() -> argparse.Namespace:
    defaults = CleaningConfig()
    parser = argparse.ArgumentParser(
        description="Conservatively filter a raw pYIN contour without note segmentation."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review-output", type=Path, default=DEFAULT_REVIEW_OUTPUT)
    parser.add_argument("--low-confidence-threshold", type=float, default=defaults.low_confidence_threshold)
    parser.add_argument("--medium-confidence-threshold", type=float, default=defaults.medium_confidence_threshold)
    parser.add_argument("--max-short-unreliable-region-frames", type=int, default=defaults.max_short_unreliable_region_frames)
    parser.add_argument("--short-region-max-mean-confidence", type=float, default=defaults.short_region_max_mean_confidence)
    parser.add_argument("--max-interpolated-gap-frames", type=int, default=defaults.max_interpolated_gap_frames)
    parser.add_argument("--max-gap-boundary-difference-cents", type=float, default=defaults.max_gap_boundary_difference_cents)
    parser.add_argument("--spike-max-duration-frames", type=int, default=defaults.spike_max_duration_frames)
    parser.add_argument("--spike-support-frames", type=int, default=defaults.spike_support_frames)
    parser.add_argument("--spike-support-agreement-cents", type=float, default=defaults.spike_support_agreement_cents)
    parser.add_argument("--spike-deviation-cents", type=float, default=defaults.spike_deviation_cents)
    parser.add_argument("--frequency-boundary-margin-hz", type=float, default=defaults.frequency_boundary_margin_hz)
    parser.add_argument("--interpolation-confidence-scale", type=float, default=defaults.interpolation_confidence_scale)
    return parser.parse_args()


def config_from_args(args: argparse.Namespace) -> CleaningConfig:
    config = CleaningConfig(
        low_confidence_threshold=args.low_confidence_threshold,
        medium_confidence_threshold=args.medium_confidence_threshold,
        max_short_unreliable_region_frames=args.max_short_unreliable_region_frames,
        short_region_max_mean_confidence=args.short_region_max_mean_confidence,
        max_interpolated_gap_frames=args.max_interpolated_gap_frames,
        max_gap_boundary_difference_cents=args.max_gap_boundary_difference_cents,
        spike_max_duration_frames=args.spike_max_duration_frames,
        spike_support_frames=args.spike_support_frames,
        spike_support_agreement_cents=args.spike_support_agreement_cents,
        spike_deviation_cents=args.spike_deviation_cents,
        frequency_boundary_margin_hz=args.frequency_boundary_margin_hz,
        interpolation_confidence_scale=args.interpolation_confidence_scale,
    )
    if not 0 <= config.low_confidence_threshold <= config.medium_confidence_threshold <= 1:
        raise ValueError("Confidence thresholds must satisfy 0 <= low <= medium <= 1.")
    if (
        config.max_short_unreliable_region_frames < 0
        or config.max_interpolated_gap_frames < 0
        or config.spike_max_duration_frames < 1
        or config.spike_support_frames < 1
    ):
        raise ValueError("Frame-count parameters must be non-negative where applicable.")
    if not 0 <= config.short_region_max_mean_confidence <= 1:
        raise ValueError("Short-region confidence must be within [0, 1].")
    if not 0 <= config.interpolation_confidence_scale <= 1:
        raise ValueError("Interpolation confidence scale must be within [0, 1].")
    if min(
        config.max_gap_boundary_difference_cents,
        config.spike_support_agreement_cents,
        config.spike_deviation_cents,
        config.frequency_boundary_margin_hz,
    ) < 0:
        raise ValueError("Pitch-distance and boundary parameters must be non-negative.")
    return config


def cents_between(first_hz: float, second_hz: float) -> float:
    """Return absolute musical distance in cents between two positive frequencies."""
    return abs(1200 * math.log2(first_hz / second_hz))


def median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def contiguous_runs(matches: list[bool]) -> list[tuple[int, int]]:
    """Return [start, end) runs for true values without altering frame timing."""
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


def confidence_class(confidence: float, config: CleaningConfig) -> str:
    if confidence < config.low_confidence_threshold:
        return "low"
    if confidence < config.medium_confidence_threshold:
        return "medium"
    return "high"


def is_valid_frequency(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def validate_raw_contour(raw: dict[str, Any]) -> list[dict[str, Any]]:
    if raw.get("timeUnit") != "seconds":
        raise ValueError("Raw contour must use seconds as its time unit.")
    frames = raw.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("Raw contour must contain at least one frame.")

    previous_time = -math.inf
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            raise ValueError(f"Frame {index} is not an object.")
        timestamp = frame.get("time")
        probability = frame.get("voicedProbability")
        if not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp):
            raise ValueError(f"Frame {index} has an invalid timestamp.")
        if timestamp <= previous_time:
            raise ValueError("Raw contour timestamps must be strictly increasing.")
        if not isinstance(probability, (int, float)) or not math.isfinite(probability):
            raise ValueError(f"Frame {index} has an invalid voiced probability.")
        if not 0 <= probability <= 1:
            raise ValueError(f"Frame {index} has a voiced probability outside [0, 1].")
        if not isinstance(frame.get("voiced"), bool):
            raise ValueError(f"Frame {index} must have a boolean voiced flag.")
        previous_time = timestamp
    return frames


def initial_processed_frames(
    raw_frames: list[dict[str, Any]], raw_config: dict[str, Any], config: CleaningConfig
) -> list[dict[str, Any]]:
    fmin = raw_config.get("fminHz")
    fmax = raw_config.get("fmaxHz")
    processed: list[dict[str, Any]] = []
    for frame in raw_frames:
        frequency = frame["frequencyHz"]
        reasons: list[str] = []
        usable = frame["voiced"] and is_valid_frequency(frequency)
        if not frame["voiced"]:
            reasons.append("rawUnvoiced")
        elif not is_valid_frequency(frequency):
            reasons.append("invalidFrequency")
        elif isinstance(fmin, (int, float)) and frequency <= fmin + config.frequency_boundary_margin_hz:
            reasons.append("atConfiguredFrequencyFloor")
        elif isinstance(fmax, (int, float)) and frequency >= fmax - config.frequency_boundary_margin_hz:
            reasons.append("atConfiguredFrequencyCeiling")

        raw_probability = float(frame["voicedProbability"])
        confidence = raw_probability if usable else 0.0
        processed.append(
            {
                "time": frame["time"],
                "frequencyHz": round(float(frequency), 6) if usable else None,
                "detectorVoiced": frame["voiced"],
                "voicedProbability": raw_probability,
                "confidence": round(confidence, 6),
                "confidenceClass": confidence_class(confidence, config),
                "status": "detected" if usable else "unavailable",
                "reasons": reasons,
            }
        )
    return processed


def reject_short_unreliable_regions(frames: list[dict[str, Any]], config: CleaningConfig) -> None:
    detected_runs = contiguous_runs([frame["status"] == "detected" for frame in frames])
    for start, end in detected_runs:
        length = end - start
        mean_confidence = sum(frame["voicedProbability"] for frame in frames[start:end]) / length
        if (
            length <= config.max_short_unreliable_region_frames
            and mean_confidence <= config.short_region_max_mean_confidence
        ):
            for frame in frames[start:end]:
                frame["frequencyHz"] = None
                frame["confidence"] = 0.0
                frame["confidenceClass"] = "low"
                frame["status"] = "rejected"
                frame["reasons"].append("shortLowConfidenceRegion")


def reject_isolated_pitch_spikes(frames: list[dict[str, Any]], config: CleaningConfig) -> None:
    # Evaluate one- and two-frame interior runs. Requiring agreement on both
    # sides protects real transitions, which establish a new pitch after change.
    for length in range(1, config.spike_max_duration_frames + 1):
        for start in range(config.spike_support_frames, len(frames) - length - config.spike_support_frames + 1):
            end = start + length
            candidates = frames[start:end]
            left = frames[start - config.spike_support_frames : start]
            right = frames[end : end + config.spike_support_frames]
            if any(frame["status"] != "detected" for frame in candidates + left + right):
                continue
            left_pitch = median([frame["frequencyHz"] for frame in left])
            right_pitch = median([frame["frequencyHz"] for frame in right])
            if cents_between(left_pitch, right_pitch) > config.spike_support_agreement_cents:
                continue
            if not all(
                cents_between(frame["frequencyHz"], left_pitch) >= config.spike_deviation_cents
                and cents_between(frame["frequencyHz"], right_pitch) >= config.spike_deviation_cents
                for frame in candidates
            ):
                continue
            for frame in candidates:
                frame["frequencyHz"] = None
                frame["confidence"] = 0.0
                frame["confidenceClass"] = "low"
                frame["status"] = "rejected"
                frame["reasons"].append("isolatedPitchSpike")


def interpolate_brief_raw_gaps(frames: list[dict[str, Any]], config: CleaningConfig) -> None:
    unavailable_runs = contiguous_runs(
        [frame["status"] == "unavailable" and frame["reasons"] == ["rawUnvoiced"] for frame in frames]
    )
    for start, end in unavailable_runs:
        if end - start > config.max_interpolated_gap_frames:
            continue
        if start < config.spike_support_frames or end + config.spike_support_frames > len(frames):
            continue
        left = frames[start - config.spike_support_frames : start]
        right = frames[end : end + config.spike_support_frames]
        if any(frame["status"] != "detected" for frame in left + right):
            continue
        support = left + right
        support_pitch = median([frame["frequencyHz"] for frame in support])
        if any(
            cents_between(frame["frequencyHz"], support_pitch)
            > config.max_gap_boundary_difference_cents
            for frame in support
        ):
            continue
        start_hz = left[-1]["frequencyHz"]
        end_hz = right[0]["frequencyHz"]
        for offset, frame in enumerate(frames[start:end], start=1):
            fraction = offset / (end - start + 1)
            interpolated_hz = start_hz * (end_hz / start_hz) ** fraction
            frame["frequencyHz"] = round(interpolated_hz, 6)
            frame["confidence"] = round(
                min(left[-1]["voicedProbability"], right[0]["voicedProbability"])
                * config.interpolation_confidence_scale,
                6,
            )
            frame["confidenceClass"] = confidence_class(frame["confidence"], config)
            frame["status"] = "interpolated"
            frame["reasons"].append("briefGapInterpolated")


def clean_frames(raw: dict[str, Any], config: CleaningConfig) -> list[dict[str, Any]]:
    raw_frames = validate_raw_contour(raw)
    raw_config = raw.get("configuration")
    if not isinstance(raw_config, dict):
        raise ValueError("Raw contour must contain a configuration object.")
    frames = initial_processed_frames(raw_frames, raw_config, config)
    reject_short_unreliable_regions(frames, config)
    reject_isolated_pitch_spikes(frames, config)
    interpolate_brief_raw_gaps(frames, config)
    return frames


def group_events(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    event_start: int | None = None
    event_key: tuple[str, tuple[str, ...]] | None = None
    for index, frame in enumerate(frames):
        key = (frame["status"], tuple(frame["reasons"]))
        is_event = frame["status"] != "detected" or bool(frame["reasons"])
        if event_start is None:
            if is_event:
                event_start, event_key = index, key
        elif not is_event or key != event_key:
            assert event_start is not None and event_key is not None
            events.append(event_from_run(frames, event_start, index, event_key))
            event_start = index if is_event else None
            event_key = key if is_event else None
    if event_start is not None and event_key is not None:
        events.append(event_from_run(frames, event_start, len(frames), event_key))
    return events


def event_from_run(
    frames: list[dict[str, Any]], start: int, end: int, key: tuple[str, tuple[str, ...]]
) -> dict[str, Any]:
    return {
        "startFrame": start,
        "endFrameExclusive": end,
        "startTime": frames[start]["time"],
        "endTime": frames[end - 1]["time"],
        "frameCount": end - start,
        "status": key[0],
        "reasons": list(key[1]),
    }


def make_summary(frames: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "totalFrames": len(frames),
        "detectedFrames": sum(frame["status"] == "detected" for frame in frames),
        "interpolatedFrames": sum(frame["status"] == "interpolated" for frame in frames),
        "unavailableFrames": sum(frame["status"] == "unavailable" for frame in frames),
        "rejectedFrames": sum(frame["status"] == "rejected" for frame in frames),
        "lowConfidenceDetectedFrames": sum(
            frame["status"] == "detected" and frame["confidenceClass"] == "low" for frame in frames
        ),
        "frequencyFloorFlaggedFrames": sum(
            "atConfiguredFrequencyFloor" in frame["reasons"] for frame in frames
        ),
    }


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    args = parse_args()
    config = config_from_args(args)
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    review_output_path = args.review_output.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Raw contour does not exist: {input_path}")

    raw = json.loads(input_path.read_text(encoding="utf-8"))
    frames = clean_frames(raw, config)
    summary = make_summary(frames)
    source_path = input_path.relative_to(REPOSITORY_ROOT).as_posix()
    output = {
        "schemaVersion": 1,
        "purpose": "Conservatively filtered pYIN pitch contour for review; not approved scoring reference data.",
        "generatedAt": datetime.now(UTC).isoformat(),
        "derivedFrom": source_path,
        "rawContourSha256": sha256_file(input_path),
        "sourceAudio": raw.get("sourceAudio"),
        "timeUnit": "seconds",
        "configuration": asdict(config),
        "summary": summary,
        "frames": frames,
    }
    review = {
        "schemaVersion": 1,
        "purpose": "Review events for the conservatively filtered pYIN contour.",
        "derivedFrom": output_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "summary": summary,
        "events": group_events(frames),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    review_output_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote filtered contour to {output_path}")
    print(f"Wrote review events to {review_output_path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
