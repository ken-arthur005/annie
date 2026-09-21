import {
  createAudioPlayer,
  type AudioPlayer,
  type AudioPlayerOptions,
  type AudioStatus,
} from "expo-audio";

import type { BundledAsset, KaraokeSong } from "@/features/songs/types";

import {
  type InstrumentalPlayback,
  type PlaybackListener,
  type PlaybackSnapshot,
  type PlaybackState,
} from "./types";

const STATUS_UPDATE_INTERVAL_MILLIS = 100;

type PlayerFactory = (source: BundledAsset, options: AudioPlayerOptions) => AudioPlayer;

type EventSubscription = {
  remove(): void;
};

const idleSnapshot: PlaybackSnapshot = {
  state: "idle",
  positionSeconds: 0,
  durationSeconds: null,
  isBuffering: false,
  error: null,
};

export class PlaybackError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PlaybackError";
  }
}

export class ExpoInstrumentalPlayback implements InstrumentalPlayback {
  private readonly listeners = new Set<PlaybackListener>();
  private readonly createPlayer: PlayerFactory;
  private player: AudioPlayer | null = null;
  private statusSubscription: EventSubscription | null = null;
  private snapshot: PlaybackSnapshot = idleSnapshot;
  private loadResolver: ((snapshot: PlaybackSnapshot) => void) | null = null;
  private loadRejecter: ((error: Error) => void) | null = null;

  constructor(createPlayer: PlayerFactory = createAudioPlayer) {
    this.createPlayer = createPlayer;
  }

  async load(song: KaraokeSong): Promise<PlaybackSnapshot> {
    await this.unload();
    this.updateSnapshot({ ...idleSnapshot, state: "loading" });

    try {
      const player = this.createPlayer(song.instrumentalAsset, {
        updateInterval: STATUS_UPDATE_INTERVAL_MILLIS,
      });
      this.player = player;
      this.statusSubscription = player.addListener("playbackStatusUpdate", (status) => {
        this.handleStatus(status);
      });

      return await new Promise<PlaybackSnapshot>((resolve, reject) => {
        this.loadResolver = resolve;
        this.loadRejecter = reject;
        this.handleStatus(player.currentStatus);
      });
    } catch (error) {
      const playbackError = toPlaybackError(error, "Could not create the instrumental player.");
      this.updateSnapshot({ ...idleSnapshot, state: "error", error: playbackError.message });
      throw playbackError;
    }
  }

  async play(): Promise<void> {
    const player = this.requirePlayer();
    if (this.snapshot.state === "ended") {
      await this.seekTo(0);
    }
    player.play();
  }

  async pause(): Promise<void> {
    this.requirePlayer().pause();
  }

  async seekTo(positionSeconds: number): Promise<void> {
    if (!Number.isFinite(positionSeconds) || positionSeconds < 0) {
      throw new PlaybackError("Playback position must be a non-negative finite number.");
    }

    const player = this.requirePlayer();
    const durationSeconds = finiteDuration(player.duration);
    const targetSeconds = durationSeconds === null ? positionSeconds : Math.min(positionSeconds, durationSeconds);

    await player.seekTo(targetSeconds);
    this.updateSnapshot({
      ...this.snapshot,
      state: player.playing ? "playing" : "paused",
      positionSeconds: targetSeconds,
      durationSeconds,
      isBuffering: player.isBuffering,
      error: null,
    });
  }

  async restart(): Promise<void> {
    await this.seekTo(0);
    await this.play();
  }

  async stop(): Promise<void> {
    const player = this.requirePlayer();
    player.pause();
    await player.seekTo(0);
    this.updateSnapshot({
      ...this.snapshot,
      state: "ready",
      positionSeconds: 0,
      durationSeconds: finiteDuration(player.duration),
      isBuffering: player.isBuffering,
      error: null,
    });
  }

  getSnapshot(): PlaybackSnapshot {
    if (!this.player) {
      return this.snapshot;
    }

    return {
      ...this.snapshot,
      positionSeconds: this.player.currentTime,
      durationSeconds: finiteDuration(this.player.duration),
      isBuffering: this.player.isBuffering,
    };
  }

  subscribe(listener: PlaybackListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  async unload(): Promise<void> {
    this.rejectPendingLoad(new PlaybackError("Instrumental playback was unloaded before it became ready."));
    this.statusSubscription?.remove();
    this.statusSubscription = null;

    if (this.player) {
      this.player.remove();
      this.player = null;
    }

    this.updateSnapshot(idleSnapshot);
  }

  private handleStatus(status: AudioStatus): void {
    if (status.error) {
      const error = new PlaybackError(status.error);
      this.updateSnapshot({
        state: "error",
        positionSeconds: status.currentTime,
        durationSeconds: finiteDuration(status.duration),
        isBuffering: status.isBuffering,
        error: error.message,
      });
      this.rejectPendingLoad(error);
      return;
    }

    const nextSnapshot: PlaybackSnapshot = {
      state: playbackStateFromStatus(status, this.snapshot.state),
      positionSeconds: status.currentTime,
      durationSeconds: finiteDuration(status.duration),
      isBuffering: status.isBuffering,
      error: null,
    };
    this.updateSnapshot(nextSnapshot);

    if (status.isLoaded) {
      this.resolvePendingLoad(nextSnapshot);
    }
  }

  private requirePlayer(): AudioPlayer {
    if (!this.player || this.snapshot.state === "loading") {
      throw new PlaybackError("Instrumental playback is not ready.");
    }

    if (this.snapshot.state === "error") {
      throw new PlaybackError(this.snapshot.error ?? "Instrumental playback failed.");
    }

    return this.player;
  }

  private updateSnapshot(snapshot: PlaybackSnapshot): void {
    this.snapshot = snapshot;
    for (const listener of this.listeners) {
      listener(snapshot);
    }
  }

  private resolvePendingLoad(snapshot: PlaybackSnapshot): void {
    this.loadResolver?.(snapshot);
    this.loadResolver = null;
    this.loadRejecter = null;
  }

  private rejectPendingLoad(error: Error): void {
    this.loadRejecter?.(error);
    this.loadResolver = null;
    this.loadRejecter = null;
  }
}

function playbackStateFromStatus(status: AudioStatus, previousState: PlaybackState): PlaybackState {
  if (!status.isLoaded) {
    return "loading";
  }

  if (status.didJustFinish) {
    return "ended";
  }

  if (status.playing) {
    return "playing";
  }

  if (previousState === "loading" || previousState === "idle") {
    return "ready";
  }

  return previousState === "ended" ? "ended" : "paused";
}

function finiteDuration(durationSeconds: number): number | null {
  return Number.isFinite(durationSeconds) && durationSeconds > 0 ? durationSeconds : null;
}

function toPlaybackError(error: unknown, fallbackMessage: string): PlaybackError {
  return error instanceof Error ? new PlaybackError(error.message) : new PlaybackError(fallbackMessage);
}
