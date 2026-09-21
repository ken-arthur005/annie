import type { LyricLine, SongPhrase, TimedLyricSegment } from "@/features/songs/types";

export type LyricLookup = {
  activePhrase: SongPhrase | null;
  activeLine: LyricLine | null;
  activeWord: TimedLyricSegment | null;
  previousLine: LyricLine | null;
  nextLine: LyricLine | null;
  wordProgress: number | null;
};
