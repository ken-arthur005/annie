import { useSyncExternalStore } from "react";

import type { KaraokeTimeline } from "./KaraokeTimeline";
import type { KaraokeTimelineSnapshot } from "./types";

const unavailableSnapshot: KaraokeTimelineSnapshot = {
  state: "idle",
  positionMs: 0 as KaraokeTimelineSnapshot["positionMs"],
  durationMs: null,
  isBuffering: false,
  error: null,
};

const subscribeToNothing = (): (() => void) => () => {};

export function useKaraokeTimeline(timeline: KaraokeTimeline | null): KaraokeTimelineSnapshot {
  return useSyncExternalStore(
    timeline ? timeline.subscribe : subscribeToNothing,
    timeline ? timeline.getUiSnapshot : () => unavailableSnapshot,
    () => unavailableSnapshot,
  );
}
