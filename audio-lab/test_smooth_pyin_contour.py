"""Regression tests for guarded continuous pitch smoothing."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smooth_pyin_contour import SmoothingConfig, smooth_frames


def frames_for(values: list[float | None]) -> list[dict[str, object]]:
    return [
        {
            "time": index * 0.01161,
            "pitchMidi": value,
            "status": "detected" if value is not None else "unavailable",
            "frequencyHz": 440.0 if value is not None else None,
            "detectorVoiced": value is not None,
            "voicedProbability": 0.8 if value is not None else 0.01,
            "confidence": 0.8 if value is not None else 0.0,
            "confidenceClass": "high" if value is not None else "low",
            "reasons": [] if value is not None else ["rawUnvoiced"],
        }
        for index, value in enumerate(values)
    ]


class SmoothPyinContourTests(unittest.TestCase):
    def test_reduces_small_jitter(self) -> None:
        source = [67.0, 67.1, 66.9, 67.1, 66.9, 67.1, 66.9, 67.1, 67.0]
        output = smooth_frames(frames_for(source), SmoothingConfig())
        smoothed = [frame["smoothedPitchMidi"] for frame in output]
        self.assertLess(np.std(smoothed[2:-2]), np.std(source[2:-2]))
        self.assertTrue(all(frame["smoothingApplied"] for frame in output[2:-2]))

    def test_preserves_linear_slide(self) -> None:
        source = [67.0 + 0.1 * index for index in range(11)]
        output = smooth_frames(frames_for(source), SmoothingConfig())
        for index in range(2, 9):
            self.assertAlmostEqual(output[index]["smoothedPitchMidi"], source[index], places=6)

    def test_preserves_vibrato_amplitude(self) -> None:
        hop_seconds = 0.01161
        source = [67.0 + 0.35 * math.sin(2 * math.pi * 5 * index * hop_seconds) for index in range(35)]
        output = smooth_frames(frames_for(source), SmoothingConfig())
        smoothed = [frame["smoothedPitchMidi"] for frame in output[2:-2]]
        source_amplitude = (max(source[2:-2]) - min(source[2:-2])) / 2
        smoothed_amplitude = (max(smoothed) - min(smoothed)) / 2
        self.assertGreater(smoothed_amplitude, source_amplitude * 0.97)

    def test_guards_hard_transition(self) -> None:
        source = [67.0] * 6 + [68.0] * 6
        output = smooth_frames(frames_for(source), SmoothingConfig())
        for index in range(4, 8):
            self.assertEqual(output[index]["smoothedPitchMidi"], source[index])
            self.assertEqual(output[index]["smoothingReason"], "transitionGuard")

    def test_short_regions_and_gaps_are_not_smoothed_across(self) -> None:
        source = [67.0, 67.1, 67.0, None, 68.0, 68.1, 68.0]
        output = smooth_frames(frames_for(source), SmoothingConfig())
        self.assertTrue(all(frame["smoothingReason"] == "shortUsableRegion" for frame in output[:3]))
        self.assertIsNone(output[3]["smoothedPitchMidi"])
        self.assertEqual(output[3]["smoothingReason"], "unavailable")
        self.assertTrue(all(frame["smoothingReason"] == "shortUsableRegion" for frame in output[4:]))


if __name__ == "__main__":
    unittest.main()
