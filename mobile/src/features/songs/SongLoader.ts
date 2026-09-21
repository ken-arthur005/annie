import type { RawSongManifestEntry } from "./rawTypes";
import type {
  ExpectedNote,
  KaraokeSong,
  LyricLine,
  ScoringRegion,
  ScoringRegionMode,
  SongId,
  SongMetadata,
  SongPhrase,
  SongSection,
  SongSectionKind,
  SongTimeMs,
  TimedLyricSegment,
} from "./types";

const SONG_ID_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const SCORING_REGION_MODES = new Set<ScoringRegionMode>([
  "stable",
  "transition",
  "uncertain",
  "suppressed",
]);
const SECTION_KINDS = new Set<SongSectionKind>([
  "intro",
  "verse",
  "pre-chorus",
  "chorus",
  "post-chorus",
  "bridge",
  "outro",
]);

export type SongLoadErrorCode =
  | "unsupported_schema"
  | "invalid_metadata"
  | "invalid_lyrics"
  | "invalid_melody"
  | "invalid_structure"
  | "missing_instrumental"
  | "cross_file_mismatch";

export type SongLoadError = {
  code: SongLoadErrorCode;
  songId?: SongId;
  message: string;
};

export type SongLoadResult = { ok: true; song: KaraokeSong } | { ok: false; error: SongLoadError };

export function loadSong(entry: RawSongManifestEntry): SongLoadResult {
  try {
    if (!Number.isFinite(entry.instrumentalAsset)) {
      throw new SongValidationFailure("missing_instrumental", "Song has no bundled instrumental asset.");
    }

    const metadata = parseMetadata(entry.metadata);
    const lyrics = parseLyrics(entry.lyrics, metadata);
    const melody = parseMelody(entry.melody, metadata);
    const structure = parseStructure(entry.structure, metadata, new Set(lyrics.lines.map((line) => line.id)));

    return {
      ok: true,
      song: {
        metadata,
        instrumentalAsset: entry.instrumentalAsset,
        artwork: entry.artwork,
        lyrics,
        melody,
        structure,
        summary: {
          id: metadata.id,
          title: metadata.title,
          artist: metadata.primaryArtist,
          durationMs: metadata.durationMs,
          artwork: entry.artwork,
        },
      },
    };
  } catch (error) {
    if (error instanceof SongValidationFailure) {
      return { ok: false, error: error.toLoadError() };
    }

    return {
      ok: false,
      error: {
        code: "invalid_metadata",
        message: "Song package could not be read.",
      },
    };
  }
}

function parseMetadata(value: unknown): SongMetadata {
  const metadata = requireRecord(value, "invalid_metadata", "metadata");
  requireSchemaVersion(metadata, "invalid_metadata");

  const id = requireSongId(metadata, "invalid_metadata");
  const durationMs = toSongTimeMs(
    requirePositiveFiniteNumber(metadata, "durationSeconds", "invalid_metadata", id),
    "invalid_metadata",
    id,
    "durationSeconds",
  );
  const assets = requireRecord(metadata.assets, "invalid_metadata", "metadata.assets", id);

  for (const assetName of ["instrumental", "lyrics", "melody", "structure"] as const) {
    requireNonEmptyString(assets, assetName, "invalid_metadata", id);
  }

  if (assets.artwork !== undefined) {
    requireNonEmptyString(assets, "artwork", "invalid_metadata", id);
  }

  return {
    id,
    title: requireNonEmptyString(metadata, "title", "invalid_metadata", id),
    primaryArtist: requireNonEmptyString(metadata, "primaryArtist", "invalid_metadata", id),
    album: requireNonEmptyString(metadata, "album", "invalid_metadata", id),
    releaseDate: requireIsoDate(metadata, "releaseDate", id),
    language: requireNonEmptyString(metadata, "language", "invalid_metadata", id),
    arrangementLabel: requireNonEmptyString(metadata, "arrangementLabel", "invalid_metadata", id),
    durationMs,
  };
}

function parseLyrics(value: unknown, metadata: SongMetadata): { lines: LyricLine[] } {
  const lyrics = requireRecord(value, "invalid_lyrics", "lyrics", metadata.id);
  requireRuntimeIdentity(lyrics, "invalid_lyrics", metadata.id, "lyrics");
  const rawLines = requireArray(lyrics, "lines", "invalid_lyrics", metadata.id);
  if (rawLines.length === 0) {
    throw new SongValidationFailure("invalid_lyrics", "Lyrics must contain at least one line.", metadata.id);
  }

  const lineIds = new Set<string>();
  const segmentIds = new Set<string>();
  let previousLineEnd = toSongTimeMs(0, "invalid_lyrics", metadata.id, "lyrics start");

  const lines = rawLines.map((rawLine, index) => {
    const line = requireRecord(rawLine, "invalid_lyrics", `lyrics.lines[${index}]`, metadata.id);
    const id = requireUniqueId(line, lineIds, "invalid_lyrics", metadata.id, `lyrics.lines[${index}]`);
    const startMs = parseBoundedTime(line, "start", metadata.durationMs, "invalid_lyrics", metadata.id, id);
    const endMs = parseBoundedTime(line, "end", metadata.durationMs, "invalid_lyrics", metadata.id, id);
    requireStrictRange(startMs, endMs, "invalid_lyrics", metadata.id, `Lyric line ${id}`);
    if (startMs < previousLineEnd) {
      throw new SongValidationFailure("invalid_lyrics", `Lyric line ${id} overlaps the previous line.`, metadata.id);
    }
    previousLineEnd = endMs;

    const rawSegments = requireArray(line, "words", "invalid_lyrics", metadata.id, id);
    if (rawSegments.length === 0) {
      throw new SongValidationFailure("invalid_lyrics", `Lyric line ${id} has no timed segments.`, metadata.id);
    }

    let previousSegmentEnd = startMs;
    const segments: TimedLyricSegment[] = rawSegments.map((rawSegment, segmentIndex) => {
      const segment = requireRecord(rawSegment, "invalid_lyrics", `lyrics.lines[${index}].words[${segmentIndex}]`, metadata.id);
      const segmentId = requireUniqueId(segment, segmentIds, "invalid_lyrics", metadata.id, "lyric segment");
      const segmentStartMs = parseBoundedTime(segment, "start", endMs, "invalid_lyrics", metadata.id, segmentId);
      const segmentEndMs = parseBoundedTime(segment, "end", endMs, "invalid_lyrics", metadata.id, segmentId);
      if (segmentStartMs < startMs || segmentEndMs < segmentStartMs || segmentStartMs < previousSegmentEnd) {
        throw new SongValidationFailure("invalid_lyrics", `Lyric segment ${segmentId} has invalid timing.`, metadata.id);
      }
      previousSegmentEnd = segmentEndMs;

      return {
        id: segmentId,
        text: requireNonEmptyString(segment, "text", "invalid_lyrics", metadata.id, segmentId),
        startMs: segmentStartMs,
        endMs: segmentEndMs,
      };
    });

    return {
      id,
      startMs,
      endMs,
      text: requireNonEmptyString(line, "text", "invalid_lyrics", metadata.id, id),
      segments,
    };
  });

  return { lines };
}

function parseMelody(value: unknown, metadata: SongMetadata): { notes: ExpectedNote[] } {
  const melody = requireRecord(value, "invalid_melody", "melody", metadata.id);
  requireRuntimeIdentity(melody, "invalid_melody", metadata.id, "melody");
  const rawNotes = requireArray(melody, "notes", "invalid_melody", metadata.id);
  if (rawNotes.length === 0) {
    throw new SongValidationFailure("invalid_melody", "Melody must contain at least one note.", metadata.id);
  }

  const noteIds = new Set<string>();
  let previousNoteStart = toSongTimeMs(0, "invalid_melody", metadata.id, "melody start");

  const notes = rawNotes.map((rawNote, index) => {
    const note = requireRecord(rawNote, "invalid_melody", `melody.notes[${index}]`, metadata.id);
    const id = requireUniqueId(note, noteIds, "invalid_melody", metadata.id, "melody note");
    const startMs = parseBoundedTime(note, "start", metadata.durationMs, "invalid_melody", metadata.id, id);
    const endMs = parseBoundedTime(note, "end", metadata.durationMs, "invalid_melody", metadata.id, id);
    requireStrictRange(startMs, endMs, "invalid_melody", metadata.id, `Melody note ${id}`);
    if (startMs < previousNoteStart) {
      throw new SongValidationFailure("invalid_melody", `Melody note ${id} is out of order.`, metadata.id);
    }
    previousNoteStart = startMs;

    const pitchMidi = requireInteger(note, "pitchMidi", "invalid_melody", metadata.id, id);
    if (pitchMidi < 0 || pitchMidi > 127) {
      throw new SongValidationFailure("invalid_melody", `Melody note ${id} has an invalid MIDI pitch.`, metadata.id);
    }

    const rawRegions = requireArray(note, "scoringRegions", "invalid_melody", metadata.id, id);
    if (rawRegions.length === 0) {
      throw new SongValidationFailure("invalid_melody", `Melody note ${id} has no scoring regions.`, metadata.id);
    }

    let previousRegionEnd = startMs;
    const scoringRegions: ScoringRegion[] = rawRegions.map((rawRegion, regionIndex) => {
      const region = requireRecord(rawRegion, "invalid_melody", `melody note ${id} region ${regionIndex}`, metadata.id);
      const regionStartMs = parseBoundedTime(region, "start", endMs, "invalid_melody", metadata.id, id);
      const regionEndMs = parseBoundedTime(region, "end", endMs, "invalid_melody", metadata.id, id);
      const mode = requireNonEmptyString(region, "mode", "invalid_melody", metadata.id, id);
      if (
        regionStartMs < startMs ||
        regionEndMs < regionStartMs ||
        regionStartMs < previousRegionEnd ||
        !SCORING_REGION_MODES.has(mode as ScoringRegionMode)
      ) {
        throw new SongValidationFailure("invalid_melody", `Melody note ${id} has an invalid scoring region.`, metadata.id);
      }
      previousRegionEnd = regionEndMs;

      const scoringWeight = requireFiniteNumber(region, "scoringWeight", "invalid_melody", metadata.id, id);
      if (scoringWeight < 0 || scoringWeight > 1) {
        throw new SongValidationFailure("invalid_melody", `Melody note ${id} has an invalid scoring weight.`, metadata.id);
      }

      return {
        startMs: regionStartMs,
        endMs: regionEndMs,
        mode: mode as ScoringRegionMode,
        scoringWeight,
      };
    });

    return {
      id,
      startMs,
      endMs,
      pitchMidi,
      noteName: requireNonEmptyString(note, "noteName", "invalid_melody", metadata.id, id),
      scoringRegions,
    };
  });

  return { notes };
}

function parseStructure(value: unknown, metadata: SongMetadata, lyricLineIds: Set<string>): { sections: SongSection[] } {
  const structure = requireRecord(value, "invalid_structure", "structure", metadata.id);
  requireRuntimeIdentity(structure, "invalid_structure", metadata.id, "structure");
  const durationMs = toSongTimeMs(
    requirePositiveFiniteNumber(structure, "songDuration", "invalid_structure", metadata.id),
    "invalid_structure",
    metadata.id,
    "songDuration",
  );
  if (durationMs !== metadata.durationMs) {
    throw new SongValidationFailure("cross_file_mismatch", "Structure duration does not match metadata duration.", metadata.id);
  }

  const rawSections = requireArray(structure, "sections", "invalid_structure", metadata.id);
  const sectionIds = new Set<string>();
  const phraseIds = new Set<string>();
  let previousSectionEnd = toSongTimeMs(0, "invalid_structure", metadata.id, "structure start");

  const sections = rawSections.map((rawSection, index) => {
    const section = requireRecord(rawSection, "invalid_structure", `structure.sections[${index}]`, metadata.id);
    const id = requireUniqueId(section, sectionIds, "invalid_structure", metadata.id, "song section");
    const startMs = parseBoundedTime(section, "start", metadata.durationMs, "invalid_structure", metadata.id, id);
    const endMs = parseBoundedTime(section, "end", metadata.durationMs, "invalid_structure", metadata.id, id);
    requireStrictRange(startMs, endMs, "invalid_structure", metadata.id, `Song section ${id}`);
    if (startMs < previousSectionEnd) {
      throw new SongValidationFailure("invalid_structure", `Song section ${id} overlaps the previous section.`, metadata.id);
    }
    previousSectionEnd = endMs;

    const kind = requireNonEmptyString(section, "kind", "invalid_structure", metadata.id, id);
    if (!SECTION_KINDS.has(kind as SongSectionKind)) {
      throw new SongValidationFailure("invalid_structure", `Song section ${id} has an unsupported kind.`, metadata.id);
    }

    let previousPhraseEnd = startMs;
    const phrases: SongPhrase[] = requireArray(section, "phrases", "invalid_structure", metadata.id, id).map(
      (rawPhrase, phraseIndex) => {
        const phrase = requireRecord(rawPhrase, "invalid_structure", `section ${id} phrase ${phraseIndex}`, metadata.id);
        const phraseId = requireUniqueId(phrase, phraseIds, "invalid_structure", metadata.id, "song phrase");
        const phraseStartMs = parseBoundedTime(phrase, "start", endMs, "invalid_structure", metadata.id, phraseId);
        const phraseEndMs = parseBoundedTime(phrase, "end", endMs, "invalid_structure", metadata.id, phraseId);
        if (phraseStartMs < startMs || phraseEndMs <= phraseStartMs || phraseStartMs < previousPhraseEnd) {
          throw new SongValidationFailure("invalid_structure", `Song phrase ${phraseId} has invalid timing.`, metadata.id);
        }
        previousPhraseEnd = phraseEndMs;

        const rawLineIds = requireArray(phrase, "lyricLineIds", "invalid_structure", metadata.id, phraseId);
        if (rawLineIds.length === 0 || rawLineIds.some((lineId) => typeof lineId !== "string" || !lyricLineIds.has(lineId))) {
          throw new SongValidationFailure("invalid_structure", `Song phrase ${phraseId} references an unknown lyric line.`, metadata.id);
        }

        return {
          id: phraseId,
          startMs: phraseStartMs,
          endMs: phraseEndMs,
          lyricLineIds: [...rawLineIds] as string[],
        };
      },
    );

    return {
      id,
      kind: kind as SongSectionKind,
      label: requireNonEmptyString(section, "label", "invalid_structure", metadata.id, id),
      startMs,
      endMs,
      phrases,
    };
  });

  return { sections };
}

function requireRuntimeIdentity(
  value: Record<string, unknown>,
  code: SongLoadErrorCode,
  songId: SongId,
  name: string,
): void {
  requireSchemaVersion(value, code, songId);
  if (value.songId !== songId) {
    throw new SongValidationFailure("cross_file_mismatch", `${name} does not match song ID ${songId}.`, songId);
  }
  if (value.timeUnit !== "seconds") {
    throw new SongValidationFailure("unsupported_schema", `${name} must use seconds as its time unit.`, songId);
  }
}

function requireSchemaVersion(value: Record<string, unknown>, code: SongLoadErrorCode, songId?: SongId): void {
  if (value.schemaVersion !== 1) {
    throw new SongValidationFailure("unsupported_schema", "Song package uses an unsupported schema version.", songId);
  }
}

function requireSongId(value: Record<string, unknown>, code: SongLoadErrorCode): SongId {
  const songId = requireNonEmptyString(value, "songId", code);
  if (!SONG_ID_PATTERN.test(songId)) {
    throw new SongValidationFailure(code, "Song ID must use lowercase kebab-case.");
  }
  return songId;
}

function parseBoundedTime(
  value: Record<string, unknown>,
  key: string,
  durationMs: SongTimeMs,
  code: SongLoadErrorCode,
  songId: SongId,
  context: string,
): SongTimeMs {
  const timeMs = toSongTimeMs(requireFiniteNumber(value, key, code, songId, context), code, songId, context);
  if (timeMs > durationMs) {
    throw new SongValidationFailure(code, `${context} ${key} exceeds the song duration.`, songId);
  }
  return timeMs;
}

function toSongTimeMs(
  seconds: number,
  code: SongLoadErrorCode,
  songId?: SongId,
  context?: string,
): SongTimeMs {
  if (seconds < 0) {
    throw new SongValidationFailure(code, `${context ?? "Time"} cannot be negative.`, songId);
  }
  const milliseconds = Math.round(seconds * 1000);
  if (!Number.isSafeInteger(milliseconds)) {
    throw new SongValidationFailure(code, `${context ?? "Time"} is outside the supported range.`, songId);
  }
  return milliseconds as SongTimeMs;
}

function requireStrictRange(
  startMs: SongTimeMs,
  endMs: SongTimeMs,
  code: SongLoadErrorCode,
  songId: SongId,
  context: string,
): void {
  if (endMs <= startMs) {
    throw new SongValidationFailure(code, `${context} must end after it starts.`, songId);
  }
}

function requireRecord(value: unknown, code: SongLoadErrorCode, context: string, songId?: SongId): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new SongValidationFailure(code, `${context} must be an object.`, songId);
  }
  return value as Record<string, unknown>;
}

function requireArray(
  value: Record<string, unknown>,
  key: string,
  code: SongLoadErrorCode,
  songId?: SongId,
  context?: string,
): unknown[] {
  const array = value[key];
  if (!Array.isArray(array)) {
    throw new SongValidationFailure(code, `${context ?? key} must be an array.`, songId);
  }
  return array;
}

function requireNonEmptyString(
  value: Record<string, unknown>,
  key: string,
  code: SongLoadErrorCode,
  songId?: SongId,
  context?: string,
): string {
  const string = value[key];
  if (typeof string !== "string" || !string.trim()) {
    throw new SongValidationFailure(code, `${context ?? key} must be a non-empty string.`, songId);
  }
  return string;
}

function requireFiniteNumber(
  value: Record<string, unknown>,
  key: string,
  code: SongLoadErrorCode,
  songId?: SongId,
  context?: string,
): number {
  const number = value[key];
  if (typeof number !== "number" || !Number.isFinite(number)) {
    throw new SongValidationFailure(code, `${context ?? key} must be a finite number.`, songId);
  }
  return number;
}

function requirePositiveFiniteNumber(
  value: Record<string, unknown>,
  key: string,
  code: SongLoadErrorCode,
  songId?: SongId,
): number {
  const number = requireFiniteNumber(value, key, code, songId);
  if (number <= 0) {
    throw new SongValidationFailure(code, `${key} must be positive.`, songId);
  }
  return number;
}

function requireInteger(
  value: Record<string, unknown>,
  key: string,
  code: SongLoadErrorCode,
  songId?: SongId,
  context?: string,
): number {
  const number = requireFiniteNumber(value, key, code, songId, context);
  if (!Number.isInteger(number)) {
    throw new SongValidationFailure(code, `${context ?? key} must be an integer.`, songId);
  }
  return number;
}

function requireUniqueId(
  value: Record<string, unknown>,
  knownIds: Set<string>,
  code: SongLoadErrorCode,
  songId: SongId,
  context: string,
): string {
  const id = requireNonEmptyString(value, "id", code, songId, context);
  if (knownIds.has(id)) {
    throw new SongValidationFailure(code, `${context} ID ${id} is duplicated.`, songId);
  }
  knownIds.add(id);
  return id;
}

function requireIsoDate(value: Record<string, unknown>, key: string, songId: SongId): string {
  const date = requireNonEmptyString(value, key, "invalid_metadata", songId);
  const parsedDate = new Date(`${date}T00:00:00Z`);
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
    Number.isNaN(parsedDate.getTime()) ||
    parsedDate.toISOString().slice(0, 10) !== date
  ) {
    throw new SongValidationFailure("invalid_metadata", "releaseDate must use ISO YYYY-MM-DD format.", songId);
  }
  return date;
}

class SongValidationFailure extends Error {
  constructor(
    readonly code: SongLoadErrorCode,
    message: string,
    readonly songId?: SongId,
  ) {
    super(message);
  }

  toLoadError(): SongLoadError {
    return { code: this.code, songId: this.songId, message: this.message };
  }
}
