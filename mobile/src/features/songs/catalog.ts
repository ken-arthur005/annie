import { songManifest } from "./manifest";
import type { KaraokeSong, SongId, SongManifestEntry, SongSummary } from "./types";

const DURATION_TOLERANCE_SECONDS = 0.01;

export class SongPackageError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SongPackageError";
  }
}

export class SongCatalog {
  private readonly songsById: ReadonlyMap<SongId, KaraokeSong>;
  private readonly summaries: readonly SongSummary[];

  constructor(manifest: readonly SongManifestEntry[]) {
    const songsById = new Map<SongId, KaraokeSong>();

    for (const entry of manifest) {
      validateManifestEntry(entry);

      const id = entry.metadata.songId;
      if (songsById.has(id)) {
        throw new SongPackageError(`Duplicate song ID in catalog: ${id}.`);
      }

      songsById.set(id, {
        ...entry,
        summary: {
          id,
          title: entry.metadata.title,
          artist: entry.metadata.primaryArtist,
          durationSeconds: entry.metadata.durationSeconds,
          artwork: entry.artwork,
        },
      });
    }

    this.songsById = songsById;
    this.summaries = [...songsById.values()].map((song) => song.summary);
  }

  listSongs(): readonly SongSummary[] {
    return this.summaries;
  }

  getSong(songId: SongId): KaraokeSong {
    const song = this.songsById.get(songId);
    if (!song) {
      throw new SongPackageError(`No prepared song is registered for ID: ${songId}.`);
    }

    return song;
  }
}

function validateManifestEntry(entry: SongManifestEntry): void {
  const { lyrics, melody, metadata, structure } = entry;
  const songId = metadata.songId;

  if (!songId || typeof songId !== "string") {
    throw new SongPackageError("Song metadata must contain a non-empty song ID.");
  }

  if (
    metadata.schemaVersion !== 1 ||
    lyrics.schemaVersion !== 1 ||
    melody.schemaVersion !== 1 ||
    structure.schemaVersion !== 1
  ) {
    throw new SongPackageError(`Song ${songId} uses an unsupported runtime schema version.`);
  }

  if (lyrics.songId !== songId || melody.songId !== songId || structure.songId !== songId) {
    throw new SongPackageError(`Runtime JSON assets do not share song ID ${songId}.`);
  }

  if (lyrics.timeUnit !== "seconds" || melody.timeUnit !== "seconds" || structure.timeUnit !== "seconds") {
    throw new SongPackageError(`Song ${songId} must use seconds as its runtime time unit.`);
  }

  if (!Number.isFinite(metadata.durationSeconds) || metadata.durationSeconds <= 0) {
    throw new SongPackageError(`Song ${songId} has an invalid metadata duration.`);
  }

  if (
    !Number.isFinite(structure.songDuration) ||
    Math.abs(structure.songDuration - metadata.durationSeconds) > DURATION_TOLERANCE_SECONDS
  ) {
    throw new SongPackageError(`Song ${songId} has inconsistent metadata and structure durations.`);
  }

  if (!Array.isArray(lyrics.lines) || !Array.isArray(melody.notes) || !Array.isArray(structure.sections)) {
    throw new SongPackageError(`Song ${songId} is missing required runtime reference data.`);
  }

  if (typeof entry.instrumentalAsset !== "number") {
    throw new SongPackageError(`Song ${songId} has no bundled instrumental asset.`);
  }
}

export const songCatalog = new SongCatalog(songManifest);
