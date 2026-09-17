"""Project-owned conversions between frequency and continuous musical pitch."""

from __future__ import annotations

import math


REFERENCE_A4_HZ = 440.0
REFERENCE_A4_MIDI = 69
NOTE_NAMES_SHARP = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def hz_to_continuous_midi(frequency_hz: float) -> float:
    """Convert a positive frequency to continuous MIDI pitch using A4 = 440 Hz."""
    if not isinstance(frequency_hz, (int, float)) or isinstance(frequency_hz, bool):
        raise ValueError("Frequency must be a positive finite number.")
    if not math.isfinite(frequency_hz) or frequency_hz <= 0:
        raise ValueError("Frequency must be a positive finite number.")
    return REFERENCE_A4_MIDI + 12 * math.log2(frequency_hz / REFERENCE_A4_HZ)


def nearest_midi(continuous_midi: float) -> int:
    """Return the nearest MIDI integer, resolving exact half-steps upward."""
    if not math.isfinite(continuous_midi):
        raise ValueError("Continuous MIDI pitch must be finite.")
    return math.floor(continuous_midi + 0.5)


def midi_to_note_name(midi: int) -> str:
    """Return a sharp note name using the MIDI convention where 60 is C4."""
    if not isinstance(midi, int) or isinstance(midi, bool):
        raise ValueError("MIDI note must be an integer.")
    return f"{NOTE_NAMES_SHARP[midi % 12]}{midi // 12 - 1}"


def cents_from_nearest_midi(continuous_midi: float, nearest_note_midi: int) -> float:
    """Return signed cents relative to the supplied nearest MIDI note."""
    if not math.isfinite(continuous_midi):
        raise ValueError("Continuous MIDI pitch must be finite.")
    if not isinstance(nearest_note_midi, int) or isinstance(nearest_note_midi, bool):
        raise ValueError("Nearest MIDI note must be an integer.")
    return 100 * (continuous_midi - nearest_note_midi)
