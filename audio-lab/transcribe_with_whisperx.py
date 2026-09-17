"""Create a reviewable WhisperX word-alignment pass for Training Season.

Run from the repository root:
    uv run --with whisperx python audio-lab/transcribe_with_whisperx.py

The canonical lyrics.json is never modified. Review the generated file before
adopting any timings as scoring reference data.
"""

from __future__ import annotations

import argparse
import json
import string
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import torch
import whisperx


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AUDIO = REPOSITORY_ROOT / "audio-lab/separated/htdemucs/TrainingSeason/vocals.wav"
DEFAULT_LYRICS = REPOSITORY_ROOT / "song_assets/training_season/runtime/lyrics.json"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "song_assets/training_season/prep/lyrics.whisperx-review.json"


def clean_word(text: str) -> str:
    """Normalize punctuation and case without changing the displayed lyric text."""
    return text.translate(str.maketrans("", "", string.punctuation)).lower()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe and word-align a reference vocal with WhisperX."
    )
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO)
    parser.add_argument("--lyrics", type=Path, default=DEFAULT_LYRICS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default="small")
    parser.add_argument("--language", default="en")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument(
        "--clean-review",
        type=Path,
        help="Replace a generated review artifact with its lyrics-only schema without running WhisperX.",
    )
    return parser.parse_args()


def flatten_words(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [word for segment in segments for word in segment.get("words", [])]


def apply_matching_word_times(
    lines: list[dict[str, Any]], aligned_words: list[dict[str, Any]]
) -> None:
    expected_words = [word for line in lines for word in line["words"]]
    expected_tokens = [clean_word(word["text"]) for word in expected_words]
    aligned_tokens = [clean_word(word["word"]) for word in aligned_words]

    # Only exact sequence matches receive a time. Near matches remain null for review.
    matches = SequenceMatcher(None, expected_tokens, aligned_tokens, autojunk=False)
    for expected_start, aligned_start, size in matches.get_matching_blocks():
        for offset in range(size):
            word = expected_words[expected_start + offset]
            aligned_word = aligned_words[aligned_start + offset]
            word["start"] = round(aligned_word["start"], 3) if "start" in aligned_word else None
            word["end"] = round(aligned_word["end"], 3) if "end" in aligned_word else None

    for line in lines:
        timed_words = [word for word in line["words"] if word["start"] is not None]
        line["start"] = timed_words[0]["start"] if timed_words else None
        line["end"] = timed_words[-1]["end"] if timed_words else None


def main() -> None:
    args = parse_args()

    if args.clean_review:
        review_path = args.clean_review.resolve()
        with review_path.open(encoding="utf-8") as file:
            review_data = json.load(file)
        lyrics = review_data.get("lyrics")
        if not isinstance(lyrics, dict):
            raise ValueError(f"Review artifact does not contain lyrics data: {review_path}")
        review_path.write_text(json.dumps(lyrics, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote lyrics-only JSON to {review_path}")
        return

    audio_path = args.audio.resolve()
    lyrics_path = args.lyrics.resolve()
    output_path = args.output.resolve()

    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
    if not lyrics_path.is_file():
        raise FileNotFoundError(f"Lyrics file does not exist: {lyrics_path}")

    with lyrics_path.open(encoding="utf-8") as file:
        lyrics_data = json.load(file)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    batch_size = args.batch_size if device == "cuda" else 1
    print(f"Using {device} with {compute_type} compute.")

    audio = whisperx.load_audio(str(audio_path))
    model = whisperx.load_model(
        args.model, device, compute_type=compute_type, language=args.language
    )
    transcript = model.transcribe(audio, batch_size=batch_size, language=args.language)

    align_model, metadata = whisperx.load_align_model(
        language_code=transcript["language"], device=device
    )
    aligned_transcript = whisperx.align(
        transcript["segments"],
        align_model,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )

    review_lyrics = json.loads(json.dumps(lyrics_data))
    apply_matching_word_times(
        review_lyrics["lines"], flatten_words(aligned_transcript["segments"])
    )

    output = {
        "schemaVersion": 1,
        "purpose": "WhisperX-generated review artifact; not approved scoring reference data.",
        "generatedAt": datetime.now(UTC).isoformat(),
        "sourceAudio": str(audio_path.relative_to(REPOSITORY_ROOT)),
        "sourceLyrics": str(lyrics_path.relative_to(REPOSITORY_ROOT)),
        "configuration": {
            "model": args.model,
            "language": transcript["language"],
            "device": device,
            "computeType": compute_type,
            "batchSize": batch_size,
        },
        "whisperxTranscript": aligned_transcript["segments"],
        "lyrics": review_lyrics,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote review artifact to {output_path}")


if __name__ == "__main__":
    main()
