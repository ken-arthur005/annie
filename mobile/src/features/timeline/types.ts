import type { PlaybackState } from "@/features/playback/types";
import type { SongTimeMs } from "@/features/songs/types";

export type KaraokeTimelineSnapshot = {
  state: PlaybackState;
  positionMs: SongTimeMs;
  durationMs: SongTimeMs | null;
  isBuffering: boolean;
  error: string | null;
};

export type KaraokeTimelineListener = (snapshot: KaraokeTimelineSnapshot) => void;
