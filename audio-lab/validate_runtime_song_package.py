"""Validate the complete shipped Training Season runtime song package.

Run from the repository root:
    audio-lab/.venv/Scripts/python.exe audio-lab/validate_runtime_song_package.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import wave
from datetime import date
from pathlib import Path
from typing import Any

from generate_runtime_melody import EPSILON, validate_runtime_melody
from generate_runtime_structure import validate_runtime_structure


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKAGE_DIRECTORY = REPOSITORY_ROOT / "song_assets/training_season/runtime"
EXPECTED_SONG_ID = "training-season-dua-lipa"
EXPECTED_ASSETS = {
    "instrumental": "instrumentals.wav",
    "lyrics": "lyrics.json",
    "melody": "melody.json",
    "structure": "structure.json",
    "artwork": "training_season_artwork.jpg",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a complete runtime karaoke song package.")
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE_DIRECTORY)
    return parser.parse_args()


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path.name}: {error.msg}") from error
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object.")
    return data


def wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as wav_file:
            if wav_file.getframerate() <= 0:
                raise ValueError("WAV sample rate must be positive.")
            return wav_file.getnframes() / wav_file.getframerate()
    except (wave.Error, EOFError) as error:
        raise ValueError(f"Could not read instrumental WAV {path.name}: {error}") from error


def validate_runtime_lyrics(lyrics: dict[str, Any], duration: float) -> None:
    if lyrics.get("schemaVersion") != 1 or lyrics.get("songId") != EXPECTED_SONG_ID or lyrics.get("timeUnit") != "seconds":
        raise ValueError("Runtime lyrics must be version 1 for Training Season in seconds.")
    lines = lyrics.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ValueError("Runtime lyrics must contain timed lines.")
    line_ids: set[str] = set()
    word_ids: set[str] = set()
    previous_line_end = -math.inf
    previous_word_end = -math.inf
    for line in lines:
        line_id, start, end = line.get("id"), line.get("start"), line.get("end")
        if not isinstance(line_id, str) or not line_id or line_id in line_ids:
            raise ValueError(f"Runtime lyrics have an invalid or duplicate line ID: {line_id!r}")
        if not all(finite_number(value) for value in (start, end)) or start >= end or end > duration + EPSILON:
            raise ValueError(f"Lyric line {line_id} has invalid timing for the instrumental duration.")
        if start < previous_line_end - EPSILON:
            raise ValueError(f"Lyric line {line_id} overlaps the previous line.")
        if not isinstance(line.get("text"), str) or not line["text"]:
            raise ValueError(f"Lyric line {line_id} has no text.")
        words = line.get("words")
        if not isinstance(words, list) or not words:
            raise ValueError(f"Lyric line {line_id} has no words.")
        line_ids.add(line_id)
        previous_line_end = end
        for word in words:
            word_id, word_start, word_end = word.get("id"), word.get("start"), word.get("end")
            if not isinstance(word_id, str) or not word_id or word_id in word_ids:
                raise ValueError(f"Runtime lyrics have an invalid or duplicate word ID: {word_id!r}")
            if not all(finite_number(value) for value in (word_start, word_end)) or word_start > word_end:
                raise ValueError(f"Lyric word {word_id} has invalid timing.")
            if word_start < start - EPSILON or word_end > end + EPSILON or word_start < previous_word_end - EPSILON:
                raise ValueError(f"Lyric word {word_id} is outside its line or unordered.")
            if not isinstance(word.get("text"), str) or not word["text"]:
                raise ValueError(f"Lyric word {word_id} has no text.")
            word_ids.add(word_id)
            previous_word_end = word_end


def validate_metadata(metadata: dict[str, Any], package_directory: Path, duration: float) -> None:
    required_text = ("purpose", "songId", "title", "primaryArtist", "album", "releaseDate", "language", "arrangementLabel")
    if metadata.get("schemaVersion") != 1 or any(not isinstance(metadata.get(field), str) or not metadata[field] for field in required_text):
        raise ValueError("Metadata is missing required schema version or display fields.")
    if metadata["songId"] != EXPECTED_SONG_ID:
        raise ValueError("Metadata song ID does not match the runtime package.")
    try:
        date.fromisoformat(metadata["releaseDate"])
    except ValueError as error:
        raise ValueError("Metadata releaseDate must use ISO YYYY-MM-DD format.") from error
    if not finite_number(metadata.get("durationSeconds")) or abs(metadata["durationSeconds"] - duration) > EPSILON:
        raise ValueError("Metadata duration does not match the instrumental WAV.")
    assets = metadata.get("assets")
    if not isinstance(assets, dict) or set(assets) != set(EXPECTED_ASSETS):
        raise ValueError("Metadata must list exactly the required runtime assets.")
    for asset_name, expected_filename in EXPECTED_ASSETS.items():
        if assets[asset_name] != expected_filename:
            raise ValueError(f"Metadata {asset_name} asset must be {expected_filename}.")
        if not (package_directory / expected_filename).is_file():
            raise ValueError(f"Metadata references missing runtime asset: {expected_filename}")


def validate_song_package(package_directory: Path) -> dict[str, int | float]:
    package_directory = package_directory.resolve()
    if not package_directory.is_dir():
        raise FileNotFoundError(f"Runtime package directory does not exist: {package_directory}")
    required_paths = {name: package_directory / filename for name, filename in EXPECTED_ASSETS.items()}
    required_paths["metadata"] = package_directory / "metadata.json"
    for name, path in required_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing runtime {name} asset: {path.name}")

    metadata = load_json(required_paths["metadata"])
    lyrics = load_json(required_paths["lyrics"])
    melody = load_json(required_paths["melody"])
    structure = load_json(required_paths["structure"])
    duration = wav_duration(required_paths["instrumental"])
    validate_metadata(metadata, package_directory, duration)
    validate_runtime_lyrics(lyrics, duration)
    validate_runtime_melody(melody)
    validate_runtime_structure(structure, lyrics)
    if abs(structure["songDuration"] - duration) > EPSILON:
        raise ValueError("Structure duration does not match the instrumental WAV.")
    if melody.get("songId") != metadata["songId"] or structure.get("songId") != metadata["songId"] or lyrics.get("songId") != metadata["songId"]:
        raise ValueError("Runtime JSON assets do not share the metadata song ID.")

    structure_lyrics = structure["sourceAssets"]["lyrics"]
    expected_lyrics_artifact = "song_assets/training_season/runtime/lyrics.json"
    if structure_lyrics["artifact"] != expected_lyrics_artifact or structure_lyrics["sha256"] != sha256_file(required_paths["lyrics"]):
        raise ValueError("Structure was not generated from the current runtime lyrics.")
    return {
        "duration": duration,
        "lineCount": len(lyrics["lines"]),
        "noteCount": len(melody["notes"]),
        "sectionCount": len(structure["sections"]),
        "phraseCount": sum(len(section["phrases"]) for section in structure["sections"]),
    }


def main() -> None:
    args = parse_args()
    summary = validate_song_package(args.package_dir)
    print("Training Season runtime package is valid.")
    print(f"Instrumental duration: {summary['duration']:.6f} seconds")
    print(f"Lyrics: {summary['lineCount']} lines")
    print(f"Melody: {summary['noteCount']} notes")
    print(f"Structure: {summary['sectionCount']} sections, {summary['phraseCount']} phrases")


if __name__ == "__main__":
    main()
