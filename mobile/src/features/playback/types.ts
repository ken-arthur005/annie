import type { KaraokeSong } from "@/features/songs/types";

export type PlaybackState =
  | "idle"
  | "loading"
  | "ready"
  | "playing"
  | "paused"
  | "ended"
  | "error";

export type PlaybackSnapshot = {
  state: PlaybackState;
  positionSeconds: number;
  durationSeconds: number | null;
  isBuffering: boolean;
  error: string | null;
};

export type PlaybackListener = (snapshot: PlaybackSnapshot) => void;

export interface InstrumentalPlayback {
  load(song: KaraokeSong): Promise<PlaybackSnapshot>;
  play(): Promise<void>;
  pause(): Promise<void>;
  seekTo(positionSeconds: number): Promise<void>;
  restart(): Promise<void>;
  stop(): Promise<void>;
  getSnapshot(): PlaybackSnapshot;
  subscribe(listener: PlaybackListener): () => void;
  unload(): Promise<void>;
}
