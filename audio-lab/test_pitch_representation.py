"""Unit tests for the project-owned continuous pitch representation."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pitch_representation import (
    cents_from_nearest_midi,
    hz_to_continuous_midi,
    midi_to_note_name,
    nearest_midi,
)
from represent_pyin_pitch import musical_frame


class PitchRepresentationTests(unittest.TestCase):
    def test_known_reference_frequencies(self) -> None:
        cases = [(440.0, 69.0, "A4"), (220.0, 57.0, "A3"), (880.0, 81.0, "A5"), (261.625565, 60.0, "C4"), (391.995436, 67.0, "G4")]
        for frequency, expected_midi, expected_note in cases:
            with self.subTest(frequency=frequency):
                continuous_midi = hz_to_continuous_midi(frequency)
                nearest_note = nearest_midi(continuous_midi)
                self.assertAlmostEqual(continuous_midi, expected_midi, places=5)
                self.assertEqual(midi_to_note_name(nearest_note), expected_note)
                self.assertAlmostEqual(
                    cents_from_nearest_midi(continuous_midi, nearest_note), 0.0, places=4
                )

    def test_preserves_continuous_deviation(self) -> None:
        above_a4 = 440.0 * 2 ** (0.25 / 12)
        below_a4 = 440.0 * 2 ** (-0.25 / 12)
        self.assertAlmostEqual(hz_to_continuous_midi(above_a4), 69.25, places=8)
        self.assertAlmostEqual(hz_to_continuous_midi(below_a4), 68.75, places=8)
        self.assertEqual(nearest_midi(69.25), 69)
        self.assertEqual(nearest_midi(68.75), 69)
        self.assertAlmostEqual(cents_from_nearest_midi(69.25, 69), 25.0)
        self.assertAlmostEqual(cents_from_nearest_midi(68.75, 69), -25.0)

    def test_half_step_rounds_upward(self) -> None:
        self.assertEqual(nearest_midi(69.5), 70)
        self.assertAlmostEqual(cents_from_nearest_midi(69.5, 70), -50.0)

    def test_invalid_frequency_is_rejected(self) -> None:
        for frequency in (0.0, -440.0, float("nan"), float("inf")):
            with self.subTest(frequency=frequency):
                with self.assertRaises(ValueError):
                    hz_to_continuous_midi(frequency)

    def test_unavailable_frame_has_null_pitch_representations(self) -> None:
        output = musical_frame(
            {
                "time": 1.0,
                "frequencyHz": None,
                "detectorVoiced": False,
                "voicedProbability": 0.01,
                "confidence": 0.0,
                "confidenceClass": "low",
                "status": "unavailable",
                "reasons": ["rawUnvoiced"],
            }
        )
        self.assertIsNone(output["pitchMidi"])
        self.assertIsNone(output["nearestMidi"])
        self.assertIsNone(output["nearestNoteName"])
        self.assertIsNone(output["centsFromNearestNote"])


if __name__ == "__main__":
    unittest.main()
