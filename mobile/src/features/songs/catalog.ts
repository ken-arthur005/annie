import { songManifest } from "./manifest";
import type { RawSongManifestEntry } from "./rawTypes";
import { loadSong, type SongLoadError } from "./SongLoader";
import type { KaraokeSong, SongId, SongSummary } from "./types";

export class SongPackageError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SongPackageError";
  }
}

export class SongCatalog {
  private readonly songsById: ReadonlyMap<SongId, KaraokeSong>;
  private readonly summaries: readonly SongSummary[];
  private readonly loadErrors: readonly SongLoadError[];

  constructor(manifest: readonly RawSongManifestEntry[]) {
    const songsById = new Map<SongId, KaraokeSong>();
    const loadErrors: SongLoadError[] = [];

    for (const entry of manifest) {
      const result = loadSong(entry);
      if (!result.ok) {
        loadErrors.push(result.error);
        continue;
      }

      const { song } = result;
      const id = song.metadata.id;
      if (songsById.has(id)) {
        loadErrors.push({
          code: "cross_file_mismatch",
          songId: id,
          message: `Duplicate song ID in catalog: ${id}.`,
        });
        continue;
      }

      songsById.set(id, song);
    }

    this.songsById = songsById;
    this.summaries = [...songsById.values()].map((song) => song.summary);
    this.loadErrors = loadErrors;
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

  getLoadErrors(): readonly SongLoadError[] {
    return this.loadErrors;
  }
}

export const songCatalog = new SongCatalog(songManifest);
