import type { ImageSourcePropType } from "react-native";

import type { BundledAsset } from "./types";

export type RawSongManifestEntry = {
  metadata: unknown;
  lyrics: unknown;
  melody: unknown;
  structure: unknown;
  instrumentalAsset: BundledAsset;
  artwork?: ImageSourcePropType;
};
