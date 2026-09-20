"""Regression tests for complete runtime song-package validation."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_runtime_song_package import validate_song_package


def write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_wav(path: Path, duration_seconds: float = 2.0) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(1000)
        wav_file.writeframes(b"\x00\x00" * int(duration_seconds * 1000))


def write_valid_package(package_directory: Path) -> None:
    write_wav(package_directory / "instrumentals.wav")
    (package_directory / "training_season_artwork.jpg").write_bytes(b"fixture artwork")
    (package_directory / "structure_guide.md").write_text("[Verse]\nFixture", encoding="utf-8")
    lyrics = {
        "schemaVersion": 1,
        "songId": "training-season-dua-lipa",
        "timeUnit": "seconds",
        "lines": [{"id": "line-1", "start": 1.0, "end": 2.0, "text": "Fixture", "words": [{"id": "word-1", "start": 1.0, "end": 2.0, "text": "Fixture"}]}],
    }
    write_json(package_directory / "lyrics.json", lyrics)
    melody = {
        "schemaVersion": 1,
        "songId": "training-season-dua-lipa",
        "timeUnit": "seconds",
        "sourcePreparation": {"artifact": "prep.json", "artifactSha256": "a", "sourceNotesSha256": "b", "sourceContourSha256": "c"},
        "notes": [{"id": "note-1", "start": 1.0, "end": 2.0, "pitchMidi": 60, "noteName": "C4", "scoringRegions": [{"start": 1.0, "end": 2.0, "mode": "stable", "scoringWeight": 1.0}]}],
    }
    write_json(package_directory / "melody.json", melody)
    structure = {
        "schemaVersion": 1,
        "songId": "training-season-dua-lipa",
        "timeUnit": "seconds",
        "songDuration": 2.0,
        "sourceAssets": {
            "lyrics": {"artifact": "song_assets/training_season/runtime/lyrics.json", "sha256": sha256(package_directory / "lyrics.json")},
            "guide": {"artifact": "song_assets/training_season/runtime/structure_guide.md", "sha256": sha256(package_directory / "structure_guide.md")},
        },
        "sections": [
            {"id": "section-intro", "kind": "intro", "label": "Intro", "start": 0.0, "end": 1.0, "phrases": []},
            {"id": "section-verse-1", "kind": "verse", "label": "Verse 1", "start": 1.0, "end": 2.0, "phrases": [{"id": "phrase-1", "start": 1.0, "end": 2.0, "lyricLineIds": ["line-1"]}]},
        ],
    }
    write_json(package_directory / "structure.json", structure)
    metadata = {
        "schemaVersion": 1,
        "purpose": "Fixture",
        "songId": "training-season-dua-lipa",
        "title": "Fixture",
        "primaryArtist": "Fixture",
        "album": "Fixture",
        "releaseDate": "2024-01-01",
        "language": "en",
        "arrangementLabel": "Fixture",
        "durationSeconds": 2.0,
        "assets": {"instrumental": "instrumentals.wav", "lyrics": "lyrics.json", "melody": "melody.json", "structure": "structure.json", "artwork": "training_season_artwork.jpg"},
    }
    write_json(package_directory / "metadata.json", metadata)


class ValidateRuntimeSongPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.package_directory = Path(self.temporary_directory.name)
        write_valid_package(self.package_directory)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_accepts_complete_consistent_package(self) -> None:
        self.assertEqual(validate_song_package(self.package_directory)["noteCount"], 1)

    def test_rejects_missing_referenced_asset(self) -> None:
        (self.package_directory / "training_season_artwork.jpg").unlink()
        with self.assertRaisesRegex(FileNotFoundError, "artwork"):
            validate_song_package(self.package_directory)

    def test_rejects_mismatched_song_id(self) -> None:
        melody_path = self.package_directory / "melody.json"
        melody = json.loads(melody_path.read_text(encoding="utf-8"))
        melody["songId"] = "different-song"
        write_json(melody_path, melody)
        with self.assertRaisesRegex(ValueError, "do not share"):
            validate_song_package(self.package_directory)

    def test_rejects_lyric_timing_past_instrumental_end(self) -> None:
        lyrics_path = self.package_directory / "lyrics.json"
        lyrics = json.loads(lyrics_path.read_text(encoding="utf-8"))
        lyrics["lines"][0]["end"] = 2.1
        lyrics["lines"][0]["words"][0]["end"] = 2.1
        write_json(lyrics_path, lyrics)
        with self.assertRaisesRegex(ValueError, "instrumental duration"):
            validate_song_package(self.package_directory)

    def test_rejects_metadata_duration_mismatch(self) -> None:
        metadata_path = self.package_directory / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["durationSeconds"] = 2.1
        write_json(metadata_path, metadata)
        with self.assertRaisesRegex(ValueError, "Metadata duration"):
            validate_song_package(self.package_directory)


if __name__ == "__main__":
    unittest.main()
