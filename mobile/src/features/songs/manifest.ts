import trainingSeasonLyrics from "../../../assets/songs/training_season/runtime/lyrics.json";
import trainingSeasonMelody from "../../../assets/songs/training_season/runtime/melody.json";
import trainingSeasonMetadata from "../../../assets/songs/training_season/runtime/metadata.json";
import trainingSeasonStructure from "../../../assets/songs/training_season/runtime/structure.json";

import type { RawSongManifestEntry } from "./rawTypes";

export const songManifest = [
  {
    metadata: trainingSeasonMetadata,
    lyrics: trainingSeasonLyrics,
    melody: trainingSeasonMelody,
    structure: trainingSeasonStructure,
    instrumentalAsset: require("../../../assets/songs/training_season/runtime/instrumentals.wav"),
    artwork: require("../../../assets/songs/training_season/runtime/training_season_artwork.jpg"),
  },
] satisfies readonly RawSongManifestEntry[];
