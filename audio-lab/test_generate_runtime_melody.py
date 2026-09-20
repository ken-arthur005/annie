"""Regression tests for runtime melody generation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_runtime_melody import validate_runtime_melody


def melody_with_regions(regions: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "songId": "fixture-song",
        "timeUnit": "seconds",
        "sourcePreparation": {
            "artifact": "song_assets/fixture/prep/analysis.json",
            "artifactSha256": "a",
            "sourceNotesSha256": "b",
            "sourceContourSha256": "c",
        },
        "notes": [{"id": "note-001", "start": 1.0, "end": 2.0, "pitchMidi": 60, "noteName": "C4", "scoringRegions": regions}],
    }


class GenerateRuntimeMelodyTests(unittest.TestCase):
    def test_accepts_full_approved_region_coverage(self) -> None:
        validate_runtime_melody(melody_with_regions([
            {"start": 1.0, "end": 1.4, "mode": "stable", "scoringWeight": 1.0},
            {"start": 1.4, "end": 1.6, "mode": "transition", "scoringWeight": 0.0},
            {"start": 1.6, "end": 2.0, "mode": "uncertain", "scoringWeight": 0.5},
        ]))

    def test_rejects_region_gaps(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-contiguous"):
            validate_runtime_melody(melody_with_regions([
                {"start": 1.0, "end": 1.4, "mode": "stable", "scoringWeight": 1.0},
                {"start": 1.5, "end": 2.0, "mode": "stable", "scoringWeight": 1.0},
            ]))

    def test_rejects_incorrect_mode_weight(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid scoring mode or weight"):
            validate_runtime_melody(melody_with_regions([
                {"start": 1.0, "end": 2.0, "mode": "transition", "scoringWeight": 1.0},
            ]))


if __name__ == "__main__":
    unittest.main()
