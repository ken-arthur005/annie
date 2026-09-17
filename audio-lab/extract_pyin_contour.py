"""Extract a raw, reviewable pYIN contour from a prepared reference vocal.

This deliberately does not smooth pitch, convert Hz to musical pitch, or create
notes. Those are separate preparation stages so the original detector output
remains available for inspection.

Run from the repository root:
    audio-lab/.venv/Scripts/python.exe audio-lab/extract_pyin_contour.py
"""

from __future__ import annotations

import argparse
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path

import librosa


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AUDIO = REPOSITORY_ROOT / "audio-lab/separated/htdemucs/TrainingSeason/vocals.wav"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/pitch.pyin-raw.json"

# A deliberately broad adult singing range. This limits impossible F0 estimates
# without discarding the reference singer's expected register.
FMIN_HZ = librosa.note_to_hz("C3")
FMAX_HZ = librosa.note_to_hz("C6")
FRAME_LENGTH = 2048
HOP_LENGTH = 512


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract the unprocessed pYIN pitch contour from a reference vocal."
    )
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def finite_or_none(value: float) -> float | None:
    """Convert pYIN's NaN sentinel into JSON's explicit null."""
    return round(float(value), 6) if math.isfinite(value) else None


def main() -> None:
    args = parse_args()
    audio_path = args.audio.resolve()
    output_path = args.output.resolve()

    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file does not exist: {audio_path}")

    samples, sample_rate = librosa.load(audio_path, sr=None, mono=True)
    started_at = time.perf_counter()
    frequencies_hz, voiced_flags, voiced_probabilities = librosa.pyin(
        samples,
        fmin=FMIN_HZ,
        fmax=FMAX_HZ,
        sr=sample_rate,
        frame_length=FRAME_LENGTH,
        hop_length=HOP_LENGTH,
        fill_na=float("nan"),
    )
    elapsed_seconds = time.perf_counter() - started_at
    timestamps = librosa.times_like(frequencies_hz, sr=sample_rate, hop_length=HOP_LENGTH)

    if not (
        len(frequencies_hz)
        == len(voiced_flags)
        == len(voiced_probabilities)
        == len(timestamps)
    ):
        raise RuntimeError("pYIN returned mismatched contour array lengths.")

    frames = [
        {
            "time": round(float(timestamp), 6),
            "frequencyHz": finite_or_none(frequency_hz),
            "voiced": bool(voiced),
            "voicedProbability": round(float(probability), 6),
        }
        for timestamp, frequency_hz, voiced, probability in zip(
            timestamps, frequencies_hz, voiced_flags, voiced_probabilities, strict=True
        )
    ]

    source_audio = audio_path.relative_to(REPOSITORY_ROOT).as_posix()
    artifact = {
        "schemaVersion": 1,
        "purpose": "Raw pYIN pitch contour for review; not approved scoring reference data.",
        "generatedAt": datetime.now(UTC).isoformat(),
        "sourceAudio": source_audio,
        "timeUnit": "seconds",
        "configuration": {
            "detector": "librosa.pyin",
            "librosaVersion": librosa.__version__,
            "sampleRateHz": sample_rate,
            "fminHz": round(float(FMIN_HZ), 6),
            "fmaxHz": round(float(FMAX_HZ), 6),
            "frameLength": FRAME_LENGTH,
            "hopLength": HOP_LENGTH,
            "frameDurationMs": round(FRAME_LENGTH / sample_rate * 1000, 6),
            "hopDurationMs": round(HOP_LENGTH / sample_rate * 1000, 6),
        },
        "audioDurationSeconds": round(len(samples) / sample_rate, 6),
        "analysisDurationSeconds": round(elapsed_seconds, 6),
        "frames": frames,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")

    voiced_count = sum(frame["voiced"] for frame in frames)
    print(f"Wrote {len(frames)} raw pYIN frames to {output_path}")
    print(f"Voiced frames: {voiced_count} ({voiced_count / len(frames):.1%})")
    print(f"Analysis time: {elapsed_seconds:.2f}s")


if __name__ == "__main__":
    main()
