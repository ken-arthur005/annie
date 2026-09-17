"""Synthetic regression tests for expression-tolerant note refinement."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refine_pyin_note_expression import RefinementConfig, refine_notes


HOP = 0.01161


def note(identifier: str, start: int, end: int, pitch: int, confidence: float = 0.8) -> dict[str, object]:
    return {
        "id": identifier,
        "start": start * HOP - HOP / 2,
        "end": end * HOP - HOP / 2,
        "pitchMidi": pitch,
        "representativePitchMidi": float(pitch),
        "frameStartIndex": start,
        "frameEndIndexExclusive": end,
        "meanConfidence": confidence,
        "lowConfidenceFrameFraction": 0.0,
    }


def frames_for(values: list[float], confidence: float = 0.8) -> list[dict[str, object]]:
    return [
        {"time": index * HOP, "smoothedPitchMidi": value, "status": "detected", "confidence": confidence}
        for index, value in enumerate(values)
    ]


class RefinePyinNoteExpressionTests(unittest.TestCase):
    def test_vibrato_like_note_remains_stable(self) -> None:
        frames = frames_for([67 + 0.25 * math.sin(index * 0.7) for index in range(24)])
        notes, review = refine_notes([note("a", 0, 24, 67)], frames, RefinementConfig())
        self.assertEqual(notes[0]["scoringMode"], "stable")
        self.assertEqual(notes[0]["scoringRegions"][0]["mode"], "stable")
        self.assertEqual(review["transitions"], [])

    def test_monotonic_slide_is_transition_not_extra_target(self) -> None:
        values = [67.0] * 10 + [67.1 + 0.1 * index for index in range(10)] + [68.0] * 10
        frames = frames_for(values)
        notes, review = refine_notes([note("a", 0, 15, 67), note("b", 15, 30, 68)], frames, RefinementConfig())
        self.assertEqual(len(review["transitions"]), 1)
        self.assertIn("transition", [region["mode"] for region in notes[0]["scoringRegions"]])
        self.assertIn("transition", [region["mode"] for region in notes[1]["scoringRegions"]])

    def test_short_return_to_target_overshoot_is_suppressed(self) -> None:
        frames = frames_for([67.0] * 10 + [67.15, 67.3] + [67.45, 67.7, 68.0, 68.3, 68.5, 68.2, 67.9, 67.6] + [67.3, 67.15] + [67.0] * 10)
        source = [note("a", 0, 12, 67), note("b", 12, 20, 68), note("c", 20, 32, 67)]
        notes, review = refine_notes(source, frames, RefinementConfig())
        self.assertEqual(notes[1]["scoringMode"], "suppressed")
        self.assertEqual(review["suppressedOvershootNoteIds"], ["b"])

    def test_low_confidence_note_is_uncertain(self) -> None:
        frames = frames_for([67.0] * 12, confidence=0.05)
        low_confidence_note = note("a", 0, 12, 67, confidence=0.05)
        low_confidence_note["lowConfidenceFrameFraction"] = 1.0
        notes, _ = refine_notes([low_confidence_note], frames, RefinementConfig())
        self.assertEqual(notes[0]["scoringMode"], "uncertain")
        self.assertEqual(notes[0]["scoringWeight"], 0.5)

    def test_sustained_pitch_change_keeps_stable_interiors(self) -> None:
        frames = frames_for([67.0] * 14 + [68.0] * 14)
        notes, review = refine_notes([note("a", 0, 14, 67), note("b", 14, 28, 68)], frames, RefinementConfig())
        self.assertEqual(len(review["transitions"]), 0)
        self.assertEqual([entry["scoringMode"] for entry in notes], ["stable", "stable"])
        self.assertEqual([entry["scoringRegions"][0]["mode"] for entry in notes], ["stable", "stable"])


if __name__ == "__main__":
    unittest.main()
