import type { ImageSourcePropType } from "react-native";

export type SongId = string;

// Metro returns a numeric module ID for statically required audio assets.
export type BundledAsset = number;

export type SongSummary = {
  id: SongId;
  title: string;
  artist: string;
  durationSeconds: number;
  artwork?: ImageSourcePropType;
};

export type RuntimeSongMetadata = {
  schemaVersion: 1;
  purpose: string;
  songId: SongId;
  title: string;
  primaryArtist: string;
  album: string;
  releaseDate: string;
  language: string;
  arrangementLabel: string;
  durationSeconds: number;
  assets: {
    instrumental: string;
    lyrics: string;
    melody: string;
    structure: string;
    artwork?: string;
  };
};

export type TimedLyricSegment = {
  id: string;
  text: string;
  start: number;
  end: number;
};

export type LyricLine = {
  id: string;
  start: number;
  end: number;
  text: string;
  words: TimedLyricSegment[];
};

export type TimedLyrics = {
  schemaVersion: 1;
  songId: SongId;
  timeUnit: "seconds";
  lines: LyricLine[];
};

export type ScoringRegionMode = "stable" | "transition" | "uncertain" | "suppressed";

export type ScoringRegion = {
  start: number;
  end: number;
  mode: ScoringRegionMode;
  scoringWeight: number;
};

export type ExpectedNote = {
  id: string;
  start: number;
  end: number;
  pitchMidi: number;
  noteName: string;
  scoringRegions: ScoringRegion[];
};

export type MelodySourcePreparation = {
  artifact: string;
  artifactSha256: string;
  sourceNotesSha256: string;
  sourceContourSha256: string;
};

export type MelodyAnswerKey = {
  schemaVersion: 1;
  purpose: string;
  songId: SongId;
  timeUnit: "seconds";
  sourcePreparation: MelodySourcePreparation;
  notes: ExpectedNote[];
};

export type SongPhrase = {
  id: string;
  start: number;
  end: number;
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
  start: number;
  end: number;
  phrases: SongPhrase[];
};

export type SongStructure = {
  schemaVersion: 1;
  purpose: string;
  songId: SongId;
  timeUnit: "seconds";
  songDuration: number;
  sourceAssets: {
    lyrics: {
      artifact: string;
      sha256: string;
    };
    guide: {
      artifact: string;
      sha256: string;
    };
  };
  sections: SongSection[];
};

export type SongManifestEntry = {
  metadata: RuntimeSongMetadata;
  lyrics: TimedLyrics;
  melody: MelodyAnswerKey;
  structure: SongStructure;
  instrumentalAsset: BundledAsset;
  artwork?: ImageSourcePropType;
};

export type KaraokeSong = SongManifestEntry & {
  summary: SongSummary;
};
