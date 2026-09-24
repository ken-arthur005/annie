import type { LyricLine, SongPhrase, TimedLyricSegment } from "@/features/songs/types";

export type LyricRail = {
  topLine: LyricLine | null;
  centerLine: LyricLine | null;
  bottomLine: LyricLine | null;
  transitionDurationMs: number | null;
};

export type LyricLookup = {
  activePhrase: SongPhrase | null;
  activeLine: LyricLine | null;
  activeWord: TimedLyricSegment | null;
  previousLine: LyricLine | null;
  nextLine: LyricLine | null;
  rail: LyricRail;
  wordProgress: number | null;
};
