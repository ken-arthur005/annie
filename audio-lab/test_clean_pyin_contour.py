"""Synthetic regression tests for conservative pYIN contour cleaning."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_pyin_contour import CleaningConfig, clean_frames


def raw_contour(values: list[tuple[float | None, bool, float]]) -> dict[str, object]:
    return {
        "timeUnit": "seconds",
        "configuration": {"fminHz": 80.0, "fmaxHz": 1200.0},
        "frames": [
            {
                "time": round(index * 0.01, 3),
                "frequencyHz": frequency,
                "voiced": voiced,
                "voicedProbability": probability,
            }
            for index, (frequency, voiced, probability) in enumerate(values)
        ],
    }


class CleanPyinContourTests(unittest.TestCase):
    def test_retains_coherent_low_confidence_passage(self) -> None:
        frames = clean_frames(raw_contour([(440.0, True, 0.03)] * 6), CleaningConfig())
        self.assertTrue(all(frame["status"] == "detected" for frame in frames))
        self.assertTrue(all(frame["frequencyHz"] == 440.0 for frame in frames))

    def test_rejects_short_low_confidence_voiced_island(self) -> None:
        frames = clean_frames(
            raw_contour([(None, False, 0.01), (440.0, True, 0.02), (440.0, True, 0.02), (None, False, 0.01)]),
            CleaningConfig(),
        )
        self.assertEqual([frame["status"] for frame in frames[1:3]], ["rejected", "rejected"])
        self.assertTrue(all(frame["frequencyHz"] is None for frame in frames[1:3]))

    def test_rejects_one_frame_rebound_spike(self) -> None:
        frames = clean_frames(
            raw_contour([(440.0, True, 0.8), (440.0, True, 0.8), (660.0, True, 0.2), (440.0, True, 0.8), (440.0, True, 0.8)]),
            CleaningConfig(),
        )
        self.assertEqual(frames[2]["status"], "rejected")
        self.assertIn("isolatedPitchSpike", frames[2]["reasons"])

    def test_retains_persistent_pitch_transition_and_vibrato(self) -> None:
        transition = clean_frames(
            raw_contour([(440.0, True, 0.8), (440.0, True, 0.8), (660.0, True, 0.8), (660.0, True, 0.8), (660.0, True, 0.8)]),
            CleaningConfig(),
        )
        vibrato = clean_frames(
            raw_contour([(440.0, True, 0.8), (450.0, True, 0.8), (440.0, True, 0.8), (431.0, True, 0.8), (440.0, True, 0.8)]),
            CleaningConfig(),
        )
        self.assertTrue(all(frame["status"] == "detected" for frame in transition + vibrato))

    def test_interpolates_only_brief_stable_raw_gap(self) -> None:
        frames = clean_frames(
            raw_contour([(440.0, True, 0.8), (440.0, True, 0.8), (None, False, 0.01), (None, False, 0.01), (440.0, True, 0.8), (440.0, True, 0.8)]),
            CleaningConfig(),
        )
        self.assertEqual([frame["status"] for frame in frames[2:4]], ["interpolated", "interpolated"])
        self.assertTrue(all(frame["detectorVoiced"] is False for frame in frames[2:4]))
        self.assertTrue(all(frame["frequencyHz"] == 440.0 for frame in frames[2:4]))

    def test_does_not_interpolate_long_or_transition_gap(self) -> None:
        long_gap = clean_frames(
            raw_contour([(440.0, True, 0.8), (440.0, True, 0.8), (None, False, 0.01), (None, False, 0.01), (None, False, 0.01), (440.0, True, 0.8), (440.0, True, 0.8)]),
            CleaningConfig(),
        )
        transition_gap = clean_frames(
            raw_contour([(440.0, True, 0.8), (440.0, True, 0.8), (None, False, 0.01), (660.0, True, 0.8), (660.0, True, 0.8)]),
            CleaningConfig(),
        )
        self.assertTrue(all(frame["status"] == "unavailable" for frame in long_gap[2:5]))
        self.assertEqual(transition_gap[2]["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
