"""Merge canonical Training Season lyrics with full-timeline WhisperX timings.

The canonical lyric text remains authoritative. WhisperX tokens supply timing only.
Run from the repository root:
    audio-lab/.venv/Scripts/python.exe audio-lab/merge_lyrics_whisperx_timing.py
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_PATH = REPOSITORY_ROOT / "song_assets/training_season/runtime/lyrics.json"
WHISPERX_PATH = REPOSITORY_ROOT / "song_assets/training_season/prep/lyrics.whisperx-review.json"
OUTPUT_PATH = REPOSITORY_ROOT / "song_assets/training_season/runtime/lyricss.json"


@dataclass(frozen=True)
class CanonicalWord:
    line_index: int
    word: dict[str, Any]


def normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def flatten_canonical(lyrics: dict[str, Any]) -> list[CanonicalWord]:
    return [
        CanonicalWord(line_index, word)
        for line_index, line in enumerate(lyrics["lines"])
        for word in line["words"]
    ]


def flatten_whisperx(review: dict[str, Any]) -> list[dict[str, Any]]:
    return [word for segment in review["whisperxTranscript"] for word in segment["words"]]


def make_timed_word(canonical_words: list[CanonicalWord], source_words: list[dict[str, Any]]) -> dict[str, Any]:
    first = canonical_words[0].word
    return {
        "id": first["id"],
        "text": " ".join(word.word["text"] for word in canonical_words),
        "start": source_words[0]["start"],
        "end": source_words[-1]["end"],
    }


def make_unresolved_word(canonical_word: CanonicalWord) -> dict[str, Any]:
    return {"id": canonical_word.word["id"], "text": canonical_word.word["text"], "start": None, "end": None}


def append_source_insertion(output: list[dict[str, Any]], source_words: list[dict[str, Any]]) -> None:
    if not source_words:
        return
    if not output:
        raise ValueError("WhisperX begins with an insertion before any canonical lyric word.")
    output[-1]["end"] = source_words[-1]["end"]


def merge_replace_block(
    canonical_words: list[CanonicalWord], source_words: list[dict[str, Any]], output: list[dict[str, Any]]
) -> None:
    """Transfer an ordered replacement block without changing canonical text."""
    canonical_index = source_index = 0
    while canonical_index < len(canonical_words) and source_index < len(source_words):
        canonical = canonical_words[canonical_index]

        # This is the sole permitted many-WhisperX-to-one-canonical mapping.
        if (
            normalized(canonical.word["text"]) == "straighttalking"
            and source_index + 1 < len(source_words)
            and normalized(source_words[source_index]["word"]) == "straight"
            and normalized(source_words[source_index + 1]["word"]) == "talking"
        ):
            output.append(make_timed_word([canonical], source_words[source_index : source_index + 2]))
            canonical_index += 1
            source_index += 2
            continue

        remaining_canonical = len(canonical_words) - canonical_index
        remaining_source = len(source_words) - source_index
        if remaining_canonical > remaining_source:
            # One WhisperX token must cover the remaining canonical words.
            output.append(make_timed_word(canonical_words[canonical_index:], [source_words[source_index]]))
            return

        output.append(make_timed_word([canonical], [source_words[source_index]]))
        canonical_index += 1
        source_index += 1

    if canonical_index < len(canonical_words):
        # WhisperX has no counterpart. These stay explicitly unresolved for manual timing.
        output.extend(make_unresolved_word(word) for word in canonical_words[canonical_index:])
    elif source_index < len(source_words):
        append_source_insertion(output, source_words[source_index:])


def merge_timing(canonical: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    canonical_words = flatten_canonical(canonical)
    source_words = flatten_whisperx(review)
    matcher = SequenceMatcher(
        None,
        [normalized(item.word["text"]) for item in canonical_words],
        [normalized(item["word"]) for item in source_words],
        autojunk=False,
    )
    output_words: list[dict[str, Any]] = []
    output_line_indices: list[int] = []

    def append_for_lines(words: list[CanonicalWord], before_count: int) -> None:
        output_line_indices.extend(word.line_index for word in words[: len(output_words) - before_count])

    for tag, canonical_start, canonical_end, source_start, source_end in matcher.get_opcodes():
        expected = canonical_words[canonical_start:canonical_end]
        observed = source_words[source_start:source_end]
        before_count = len(output_words)
        if tag == "equal":
            output_words.extend(make_timed_word([word], [source]) for word, source in zip(expected, observed, strict=True))
        elif tag == "replace":
            merge_replace_block(expected, observed, output_words)
        elif tag == "delete":
            output_words.extend(make_unresolved_word(word) for word in expected)
        elif tag == "insert":
            append_source_insertion(output_words, observed)
        else:
            raise ValueError(f"Unsupported sequence alignment operation: {tag}")
        append_for_lines(expected, before_count)

    output = deepcopy(canonical)
    output["lines"] = []
    for line_index, source_line in enumerate(canonical["lines"]):
        line_words = [
            word for word, word_line_index in zip(output_words, output_line_indices, strict=True)
            if word_line_index == line_index
        ]
        line = {"id": source_line["id"], "start": None, "end": None, "text": source_line["text"], "words": line_words}
        timed = [word for word in line_words if word["start"] is not None]
        if timed:
            line["start"] = timed[0]["start"]
            line["end"] = timed[-1]["end"]
        output["lines"].append(line)
    return output


def apply_reviewed_overrides(lyrics: dict[str, Any], canonical: dict[str, Any]) -> None:
    """Correct sequence-alignment ambiguities with the reviewed chronological mapping."""
    canonical_words = {word["id"]: word for line in canonical["lines"] for word in line["words"]}
    lines = {line["id"]: line for line in lyrics["lines"]}

    def timed(identifier: str, start: float, end: float, text: str | None = None) -> dict[str, Any]:
        word = canonical_words[identifier]
        return {"id": identifier, "text": word["text"] if text is None else text, "start": start, "end": end}

    def unresolved(identifier: str) -> dict[str, Any]:
        word = canonical_words[identifier]
        return {"id": identifier, "text": word["text"], "start": None, "end": None}

    # WhisperX omits this repeated line-final "I"; use the available silent gap before its next timed word.
    lines["line-9"]["words"][-1] = timed("word-67", 46.899, 47.277)
    lines["line-14"]["words"] = [
        timed("word-106", 64.43, 64.53), timed("word-107", 65.17, 65.671),
        timed("word-108", 65.691, 66.511), timed("word-109", 66.711, 66.931, "who can"),
        timed("word-111", 66.992, 67.412), timed("word-112", 67.812, 68.473),
    ]
    lines["line-12"]["words"] = [
        timed("word-92", 55.744, 56.004), timed("word-93", 56.024, 56.144),
        timed("word-94", 56.204, 56.705), timed("word-95", 56.925, 57.305),
        timed("word-96", 57.365, 58.146, "straight-talking"), timed("word-97", 58.186, 58.346),
        timed("word-98", 58.366, 58.666, "my soul"),
    ]
    lines["line-13"]["words"][-1]["end"] = 64.25
    lines["line-23"]["words"] = [
        timed("word-178", 112.088, 112.268, "Is it"), timed("word-180", 112.349, 112.749),
        timed("word-181", 112.829, 113.169), timed("word-182", 113.309, 113.55),
        timed("word-183", 113.97, 114.21), timed("word-184", 114.31, 114.911),
        timed("word-185", 115.231, 115.651), timed("word-186", 115.992, 117.213),
    ]
    lines["line-29"]["words"] = [
        timed("word-232", 139.612, 139.892), timed("word-233", 140.053, 140.133),
        timed("word-234", 140.353, 140.633), timed("word-235", 140.673, 140.793),
        timed("word-236", 140.813, 140.933, "have to"), timed("word-238", 141.033, 141.414),
        timed("word-239", 141.534, 142.054),
    ]
    lines["line-30"]["words"] = [
        timed("word-240", 143.305, 143.425), timed("word-241", 143.485, 144.026),
        timed("word-242", 144.106, 144.246), timed("word-243", 144.286, 144.506),
        timed("word-244", 144.546, 144.706), timed("word-245", 144.746, 144.946),
        timed("word-246", 145.006, 145.326, "me know,"), timed("word-248", 145.407, 146.007),
    ]
    lines["line-17"]["words"] = [
        timed("word-130", 82.078, 83.419), timed("word-131", 83.519, 83.979),
        timed("word-132", 84.36, 85.38), timed("word-133", 85.4, 85.88),
    ]
    lines["line-17"]["text"] = "'Cause training season's over"
    lines["line-18"]["words"] = [
        timed("word-137", 86.701, 86.881), timed("word-138", 86.921, 87.721),
        timed("word-139", 88.642, 88.782), timed("word-140", 88.822, 89.002),
        timed("word-141", 89.022, 89.122), timed("word-142", 89.482, 89.822),
        timed("word-143", 90.042, 90.142), timed("word-144", 90.202, 90.282),
        timed("word-145", 90.363, 90.743), timed("word-146", 90.763, 91.863),
    ]
    lines["line-39"]["words"][0] = timed("word-296", 176.192, 176.23)
    lines["line-26"]["words"] = [
        timed("word-211", 126.02, 126.26), timed("word-212", 126.34, 126.42),
        timed("word-213", 126.48, 126.961), timed("word-214", 127.201, 127.581),
        timed("word-215", 127.621, 128.402, "straight-talking"), timed("word-216", 128.422, 128.622),
        timed("word-217", 128.642, 128.882, "my soul"),
    ]
    lines["line-41"]["words"] = [
        timed("word-320", 184.436, 184.796), timed("word-321", 184.856, 184.936),
        timed("word-322", 184.996, 185.476), timed("word-323", 185.737, 186.117),
        timed("word-324", 186.137, 186.937, "straight-talking"), timed("word-325", 186.977, 187.177),
        timed("word-326", 187.197, 187.658, "my soul"),
    ]
    lines["line-41"]["text"] = "When I'm vulnerable, he's straight-talking to my soul"
    lines["line-43"]["words"] = [
        unresolved("word-343"), unresolved("word-344"), unresolved("word-345"), unresolved("word-346"),
    ]
    lines["line-43"]["text"] = "'Cause training season's over"

    for line in lyrics["lines"]:
        timed_words = [word for word in line["words"] if word["start"] is not None]
        line["start"] = timed_words[0]["start"] if timed_words else None
        line["end"] = timed_words[-1]["end"] if timed_words else None


def validate_output(lyrics: dict[str, Any]) -> None:
    unresolved_ids: list[str] = []
    previous_end = -float("inf")
    for line in lyrics["lines"]:
        for word in line["words"]:
            start, end = word["start"], word["end"]
            if (start is None) != (end is None):
                raise ValueError(f"Word {word['id']} has only one timestamp.")
            if start is None:
                unresolved_ids.append(word["id"])
                continue
            if start > end or start < previous_end:
                raise ValueError(f"Word {word['id']} has unordered timing.")
            previous_end = end
    allowed_unresolved = {
        "word-343", "word-344", "word-345", "word-346", "word-350", "word-351", "word-352",
    }
    unexpected = set(unresolved_ids) - allowed_unresolved
    if unexpected:
        raise ValueError(f"Unexpected unresolved words: {sorted(unexpected)}")


def main() -> None:
    canonical = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
    review = json.loads(WHISPERX_PATH.read_text(encoding="utf-8"))
    output = merge_timing(canonical, review)
    apply_reviewed_overrides(output, canonical)
    validate_output(output)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    unresolved = [
        word["id"] for line in output["lines"] for word in line["words"] if word["start"] is None
    ]
    print(f"Wrote merged lyrics to {OUTPUT_PATH}")
    print(f"Output words: {sum(len(line['words']) for line in output['lines'])}")
    print(f"Unresolved manual-timing words: {', '.join(unresolved)}")


if __name__ == "__main__":
    main()
