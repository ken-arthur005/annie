"""Regression tests for runtime structure validation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_runtime_structure import validate_runtime_structure


LYRICS = {"lines": [{"id": "line-1"}]}


def structure_with_sections(sections: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "songId": "training-season-dua-lipa",
        "timeUnit": "seconds",
        "songDuration": 2.0,
        "sourceAssets": {
            "lyrics": {"artifact": "lyrics.json", "sha256": "a"},
            "guide": {"artifact": "structure_guide.md", "sha256": "b"},
        },
        "sections": sections,
    }


class GenerateRuntimeStructureTests(unittest.TestCase):
    def test_accepts_contiguous_sections_and_an_instrumental_intro(self) -> None:
        validate_runtime_structure(structure_with_sections([
            {"id": "section-intro", "kind": "intro", "label": "Intro", "start": 0.0, "end": 1.0, "phrases": []},
            {"id": "section-verse-1", "kind": "verse", "label": "Verse 1", "start": 1.0, "end": 2.0, "phrases": [{"id": "phrase-001", "start": 1.0, "end": 2.0, "lyricLineIds": ["line-1"]}]},
        ]), LYRICS)

    def test_rejects_non_contiguous_sections(self) -> None:
        with self.assertRaisesRegex(ValueError, "contiguous"):
            validate_runtime_structure(structure_with_sections([
                {"id": "section-intro", "kind": "intro", "label": "Intro", "start": 0.0, "end": 0.5, "phrases": []},
                {"id": "section-verse-1", "kind": "verse", "label": "Verse 1", "start": 1.0, "end": 2.0, "phrases": []},
            ]), LYRICS)

    def test_rejects_phrase_with_missing_lyric_line(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing lyric lines"):
            validate_runtime_structure(structure_with_sections([
                {"id": "section-intro", "kind": "intro", "label": "Intro", "start": 0.0, "end": 1.0, "phrases": []},
                {"id": "section-verse-1", "kind": "verse", "label": "Verse 1", "start": 1.0, "end": 2.0, "phrases": [{"id": "phrase-001", "start": 1.0, "end": 2.0, "lyricLineIds": ["line-missing"]}]},
            ]), LYRICS)


if __name__ == "__main__":
    unittest.main()
