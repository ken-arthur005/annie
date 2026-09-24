import type {
  KaraokeSong,
  LyricLine,
  SongPhrase,
  SongTimeMs,
  TimedLyricSegment,
} from "@/features/songs/types";

import type { LyricLookup } from "./types";

type IndexedWord = {
  word: TimedLyricSegment;
  lineIndex: number;
};

type TimedItem = {
  startMs: SongTimeMs;
  endMs: SongTimeMs;
};

export class LyricTimeline {
  private readonly lines: readonly LyricLine[];
  private readonly phrases: readonly SongPhrase[];
  private readonly words: readonly IndexedWord[];

  constructor(song: KaraokeSong) {
    this.lines = song.lyrics.lines;
    this.phrases = song.structure.sections.flatMap((section) => section.phrases);
    this.words = song.lyrics.lines.flatMap((line, lineIndex) =>
      line.segments.map((word) => ({ word, lineIndex })),
    );
  }

  lookup(currentTimeMs: SongTimeMs): LyricLookup {
    const activeLineIndex = findContainingIndex(this.lines, currentTimeMs, (line) => line);
    const activeWordIndex = findContainingIndex(this.words, currentTimeMs, (entry) => entry.word);
    const activePhraseIndex = findContainingIndex(this.phrases, currentTimeMs, (phrase) => phrase);
    const activeWord = activeWordIndex === null ? null : this.words[activeWordIndex].word;

    return {
      activePhrase: activePhraseIndex === null ? null : this.phrases[activePhraseIndex],
      activeLine: activeLineIndex === null ? null : this.lines[activeLineIndex],
      activeWord,
      ...this.surroundingLines(currentTimeMs, activeLineIndex),
      rail: this.railAt(currentTimeMs, activeLineIndex),
      wordProgress: activeWord === null ? null : progressWithin(activeWord, currentTimeMs),
    };
  }

  private railAt(currentTimeMs: SongTimeMs, activeLineIndex: number | null): LyricLookup["rail"] {
    if (activeLineIndex !== null) {
      return {
        topLine: this.lines[activeLineIndex - 1] ?? null,
        centerLine: this.lines[activeLineIndex],
        bottomLine: this.lines[activeLineIndex + 1] ?? null,
        transitionDurationMs: null,
      };
    }

    const nextLineIndex = findFirstStartingAfter(this.lines, currentTimeMs, (line) => line);
    const completedLine = this.lines[nextLineIndex - 1] ?? null;
    const upcomingLine = this.lines[nextLineIndex] ?? null;
    const gapMs = upcomingLine === null
      ? 650
      : Math.max(upcomingLine.startMs - (completedLine?.endMs ?? upcomingLine.startMs), 0);

    return {
      topLine: completedLine,
      centerLine: upcomingLine,
      bottomLine: this.lines[nextLineIndex + 1] ?? null,
      transitionDurationMs: completedLine === null ? null : railTransitionDuration(gapMs),
    };
  }

  private surroundingLines(
    currentTimeMs: SongTimeMs,
    activeLineIndex: number | null,
  ): Pick<LyricLookup, "previousLine" | "nextLine"> {
    if (activeLineIndex !== null) {
      return {
        previousLine: this.lines[activeLineIndex - 1] ?? null,
        nextLine: this.lines[activeLineIndex + 1] ?? null,
      };
    }

    const nextLineIndex = findFirstStartingAfter(this.lines, currentTimeMs, (line) => line);
    return {
      previousLine: this.lines[nextLineIndex - 1] ?? null,
      nextLine: this.lines[nextLineIndex] ?? null,
    };
  }
}

function railTransitionDuration(gapMs: number): number {
  if (gapMs < 460) {
    return Math.max(220, Math.round(gapMs * 0.65));
  }

  return Math.min(Math.max(Math.round(gapMs * 0.65), 300), 1_200);
}

function findContainingIndex<T>(
  items: readonly T[],
  currentTimeMs: SongTimeMs,
  getTimedItem: (item: T) => TimedItem,
): number | null {
  const candidateIndex = findLastStartingAtOrBefore(items, currentTimeMs, getTimedItem);
  if (candidateIndex === -1) {
    return null;
  }

  return currentTimeMs < getTimedItem(items[candidateIndex]).endMs ? candidateIndex : null;
}

function findLastStartingAtOrBefore<T>(
  items: readonly T[],
  currentTimeMs: SongTimeMs,
  getTimedItem: (item: T) => TimedItem,
): number {
  let low = 0;
  let high = items.length - 1;
  let result = -1;

  while (low <= high) {
    const midpoint = Math.floor((low + high) / 2);
    if (getTimedItem(items[midpoint]).startMs <= currentTimeMs) {
      result = midpoint;
      low = midpoint + 1;
    } else {
      high = midpoint - 1;
    }
  }

  return result;
}

function findFirstStartingAfter<T>(
  items: readonly T[],
  currentTimeMs: SongTimeMs,
  getTimedItem: (item: T) => TimedItem,
): number {
  let low = 0;
  let high = items.length;

  while (low < high) {
    const midpoint = Math.floor((low + high) / 2);
    if (getTimedItem(items[midpoint]).startMs <= currentTimeMs) {
      low = midpoint + 1;
    } else {
      high = midpoint;
    }
  }

  return low;
}

function progressWithin(item: TimedItem, currentTimeMs: SongTimeMs): number {
  return (currentTimeMs - item.startMs) / (item.endMs - item.startMs);
}
