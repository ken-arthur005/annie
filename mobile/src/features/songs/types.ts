import type { ImageSourcePropType } from "react-native";

export type SongId = string;

declare const songTimeMsBrand: unique symbol;
export type SongTimeMs = number & { readonly [songTimeMsBrand]: "SongTimeMs" };

// Metro returns a numeric module ID for statically required audio assets.
export type BundledAsset = number;

export type SongSummary = {
  id: SongId;
  title: string;
  artist: string;
  durationMs: SongTimeMs;
  artwork?: ImageSourcePropType;
};

export type SongMetadata = {
  id: SongId;
  title: string;
  primaryArtist: string;
  album: string;
  releaseDate: string;
  language: string;
  arrangementLabel: string;
  durationMs: SongTimeMs;
};

export type TimedLyricSegment = {
  id: string;
  text: string;
  startMs: SongTimeMs;
  endMs: SongTimeMs;
};

export type LyricLine = {
  id: string;
  startMs: SongTimeMs;
  endMs: SongTimeMs;
  text: string;
  segments: TimedLyricSegment[];
};

export type TimedLyrics = {
  lines: LyricLine[];
};

export type ScoringRegionMode = "stable" | "transition" | "uncertain" | "suppressed";

export type ScoringRegion = {
  startMs: SongTimeMs;
  endMs: SongTimeMs;
  mode: ScoringRegionMode;
  scoringWeight: number;
};

export type ExpectedNote = {
  id: string;
  startMs: SongTimeMs;
  endMs: SongTimeMs;
  pitchMidi: number;
  noteName: string;
  scoringRegions: ScoringRegion[];
};

export type MelodyAnswerKey = {
  notes: ExpectedNote[];
};

export type SongPhrase = {
  id: string;
  startMs: SongTimeMs;
  endMs: SongTimeMs;
  lyricLineIds: string[];
};

export type SongSectionKind =
  | "intro"
  | "verse"
  | "pre-chorus"
  | "chorus"
  | "post-chorus"
  | "bridge"
  | "outro";

export type SongSection = {
  id: string;
  kind: SongSectionKind;
  label: string;
  startMs: SongTimeMs;
  endMs: SongTimeMs;
  phrases: SongPhrase[];
};

export type SongStructure = {
  sections: SongSection[];
};

export type KaraokeSong = {
  metadata: SongMetadata;
  instrumentalAsset: BundledAsset;
  artwork?: ImageSourcePropType;
  lyrics: TimedLyrics;
  melody: MelodyAnswerKey;
  structure: SongStructure;
  summary: SongSummary;
};
