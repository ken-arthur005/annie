import trainingSeasonLyrics from "../../../assets/songs/training_season/runtime/lyrics.json";
import trainingSeasonMelody from "../../../assets/songs/training_season/runtime/melody.json";
import trainingSeasonMetadata from "../../../assets/songs/training_season/runtime/metadata.json";
import trainingSeasonStructure from "../../../assets/songs/training_season/runtime/structure.json";

import type {
  MelodyAnswerKey,
  RuntimeSongMetadata,
  SongManifestEntry,
  SongStructure,
  TimedLyrics,
} from "./types";

export const songManifest = [
  {
    metadata: trainingSeasonMetadata as RuntimeSongMetadata,
    lyrics: trainingSeasonLyrics as TimedLyrics,
    melody: trainingSeasonMelody as MelodyAnswerKey,
    structure: trainingSeasonStructure as SongStructure,
    instrumentalAsset: require("../../../assets/songs/training_season/runtime/instrumentals.wav"),
    artwork: require("../../../assets/songs/training_season/runtime/training_season_artwork.jpg"),
  },
] satisfies readonly SongManifestEntry[];
