"""Synthetic regression tests for automatic expected-note segmentation."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from segment_pyin_notes import SegmentationConfig, segment_frames


def frames_for(values: list[float | None]) -> list[dict[str, object]]:
    return [
        {
            "time": index * 0.01161,
            "smoothedPitchMidi": value,
            "status": "detected" if value is not None else "unavailable",
            "confidence": 0.8 if value is not None else 0.0,
        }
        for index, value in enumerate(values)
    ]


class SegmentPyinNotesTests(unittest.TestCase):
    def test_vibrato_becomes_one_note(self) -> None:
        values = [67 + 0.35 * math.sin(index * 0.5) for index in range(24)]
        result = segment_frames(frames_for(values), SegmentationConfig())
        self.assertEqual(len(result.notes), 1)
        self.assertEqual(result.notes[0]["pitchMidi"], 67)

    def test_sustained_semitone_change_becomes_two_notes(self) -> None:
        result = segment_frames(frames_for([67.0] * 12 + [68.0] * 12), SegmentationConfig())
        self.assertEqual([note["pitchMidi"] for note in result.notes], [67, 68])
        self.assertLessEqual(result.notes[0]["end"], result.notes[1]["start"])

    def test_slide_does_not_create_intermediate_notes(self) -> None:
        values = [67.0] * 10 + [67.0 + 0.1 * index for index in range(1, 11)] + [68.0] * 10
        result = segment_frames(frames_for(values), SegmentationConfig())
        self.assertEqual([note["pitchMidi"] for note in result.notes], [67, 68])

    def test_short_ornament_is_omitted_and_logged(self) -> None:
        result = segment_frames(frames_for([67.0] * 10 + [68.0] * 4 + [67.0] * 10), SegmentationConfig())
        self.assertEqual([note["pitchMidi"] for note in result.notes], [67])
        self.assertTrue(result.ignored_candidates)

    def test_seven_frame_distinct_note_is_retained(self) -> None:
        result = segment_frames(frames_for([67.0] * 10 + [68.0] * 7), SegmentationConfig())
        self.assertEqual([note["pitchMidi"] for note in result.notes], [67, 68])

    def test_short_matching_gap_is_bridged_but_long_gap_splits(self) -> None:
        bridged = segment_frames(frames_for([67.0] * 10 + [None] * 2 + [67.0] * 10), SegmentationConfig())
        split = segment_frames(frames_for([67.0] * 10 + [None] * 4 + [67.0] * 10), SegmentationConfig())
        self.assertEqual(len(bridged.notes), 1)
        self.assertEqual(len(bridged.bridged_gaps), 1)
        self.assertEqual(len(split.notes), 2)


if __name__ == "__main__":
    unittest.main()
