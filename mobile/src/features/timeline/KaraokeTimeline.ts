import { AppState, type AppStateStatus, type NativeEventSubscription } from "react-native";

import type { InstrumentalPlayback, PlaybackSnapshot } from "@/features/playback/types";
import type { KaraokeSong, SongTimeMs } from "@/features/songs/types";

import type { KaraokeTimelineListener, KaraokeTimelineSnapshot } from "./types";

const initialSnapshot: KaraokeTimelineSnapshot = {
  state: "idle",
  positionMs: toSongTimeMs(0),
  durationMs: null,
  isBuffering: false,
  error: null,
};

export class KaraokeTimeline {
  private readonly listeners = new Set<KaraokeTimelineListener>();
  private readonly unsubscribePlayback: () => void;
  private appStateSubscription: NativeEventSubscription | null = null;
  private song: KaraokeSong | null = null;
  private snapshot = initialSnapshot;
  private disposed = false;

  constructor(private readonly playback: InstrumentalPlayback) {
    this.unsubscribePlayback = playback.subscribe((snapshot) => {
      this.updateFromPlayback(snapshot);
    });
  }

  async load(song: KaraokeSong): Promise<KaraokeTimelineSnapshot> {
    this.assertNotDisposed();
    this.stopWatchingAppState();
    this.song = song;
    this.updateFromPlayback({
      state: "loading",
      positionSeconds: 0,
      durationSeconds: null,
      isBuffering: false,
      error: null,
    });

    try {
      const playbackSnapshot = await this.playback.load(song);
      this.startWatchingAppState();
      return this.updateFromPlayback(playbackSnapshot);
    } catch (error) {
      this.song = null;
      this.stopWatchingAppState();
      this.updateSnapshot({
        ...initialSnapshot,
        state: "error",
        error: error instanceof Error ? error.message : "Could not load the instrumental.",
      });
      throw error;
    }
  }

  async play(): Promise<void> {
    this.requireSong();
    await this.playback.play();
    this.updateFromPlayback(this.playback.getSnapshot());
  }

  async pause(): Promise<void> {
    this.requireSong();
    await this.playback.pause();
    this.updateFromPlayback(this.playback.getSnapshot());
  }

  async seekTo(positionMs: SongTimeMs): Promise<void> {
    const song = this.requireSong();
    await this.playback.seekTo(songTimeMsToSeconds(clampSongTime(positionMs, song.metadata.durationMs)));
    this.updateFromPlayback(this.playback.getSnapshot());
  }

  async restart(): Promise<void> {
    this.requireSong();
    await this.playback.restart();
    this.updateFromPlayback(this.playback.getSnapshot());
  }

  async stop(): Promise<void> {
    this.requireSong();
    await this.playback.stop();
    this.updateFromPlayback(this.playback.getSnapshot());
  }

  // Event-driven UI consumers use this stable snapshot at the playback update cadence.
  getUiSnapshot = (): KaraokeTimelineSnapshot => this.snapshot;

  // Analysis consumers can request a fresh reading derived directly from native playback position.
  getSnapshot(): KaraokeTimelineSnapshot {
    this.assertNotDisposed();
    return this.toTimelineSnapshot(this.playback.getSnapshot());
  }

  subscribe = (listener: KaraokeTimelineListener): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  async dispose(): Promise<void> {
    if (this.disposed) {
      return;
    }

    this.disposed = true;
    this.stopWatchingAppState();
    this.unsubscribePlayback();
    this.listeners.clear();
    this.song = null;
    await this.playback.unload();
    this.snapshot = initialSnapshot;
  }

  private startWatchingAppState(): void {
    this.appStateSubscription ??= AppState.addEventListener("change", this.handleAppStateChange);
  }

  private stopWatchingAppState(): void {
    this.appStateSubscription?.remove();
    this.appStateSubscription = null;
  }

  private handleAppStateChange = (nextAppState: AppStateStatus): void => {
    if (nextAppState === "active" || this.snapshot.state !== "playing") {
      return;
    }

    // Resume remains explicit so playback never restarts unexpectedly after an interruption.
    void this.pause().catch((error: unknown) => {
      this.updateSnapshot({
        ...this.snapshot,
        state: "error",
        error: error instanceof Error ? error.message : "Could not pause the instrumental.",
      });
    });
  };

  private updateFromPlayback(playbackSnapshot: PlaybackSnapshot): KaraokeTimelineSnapshot {
    const snapshot = this.toTimelineSnapshot(playbackSnapshot);
    this.updateSnapshot(snapshot);
    return snapshot;
  }

  private toTimelineSnapshot(playbackSnapshot: PlaybackSnapshot): KaraokeTimelineSnapshot {
    const durationMs = this.song?.metadata.durationMs ?? null;
    const positionMs = durationMs === null
      ? toSongTimeMs(0)
      : playbackSnapshot.state === "ended"
        ? durationMs
        : clampSongTime(secondsToSongTimeMs(playbackSnapshot.positionSeconds), durationMs);

    return {
      state: playbackSnapshot.state,
      positionMs,
      durationMs,
      isBuffering: playbackSnapshot.isBuffering,
      error: playbackSnapshot.error,
    };
  }

  private updateSnapshot(snapshot: KaraokeTimelineSnapshot): void {
    this.snapshot = snapshot;
    for (const listener of this.listeners) {
      listener(snapshot);
    }
  }

  private requireSong(): KaraokeSong {
    this.assertNotDisposed();
    if (!this.song) {
      throw new Error("Karaoke timeline has no loaded song.");
    }

    return this.song;
  }

  private assertNotDisposed(): void {
    if (this.disposed) {
      throw new Error("Karaoke timeline has been disposed.");
    }
  }
}

export function secondsToSongTimeMs(seconds: number): SongTimeMs {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return toSongTimeMs(0);
  }

  return toSongTimeMs(Math.round(seconds * 1000));
}

export function songTimeMsToSeconds(milliseconds: SongTimeMs): number {
  return milliseconds / 1000;
}

function clampSongTime(positionMs: SongTimeMs, durationMs: SongTimeMs): SongTimeMs {
  return toSongTimeMs(Math.min(Math.max(positionMs, 0), durationMs));
}

function toSongTimeMs(value: number): SongTimeMs {
  return value as SongTimeMs;
}
