import { useEffect, useRef, useState } from "react";

import { LyricTimeline, type LyricLookup } from "@/features/lyrics";
import { ExpoInstrumentalPlayback } from "@/features/playback";
import type { ExpectedNote, KaraokeSong, SongTimeMs } from "@/features/songs/types";
import { KaraokeTimeline, useKaraokeTimeline } from "@/features/timeline";

const SEEK_STEP_MS = 5_000;
const LYRIC_DISPLAY_LEAD_MS = 180;

export function useKaraokeSession(song: KaraokeSong): {
  snapshot: ReturnType<typeof useKaraokeTimeline>;
  lyrics: LyricLookup;
  expectedNote: ExpectedNote | null;
  error: string | null;
  play: () => Promise<void>;
  pause: () => Promise<void>;
  restart: () => Promise<void>;
  retry: () => Promise<void>;
  seekBy: (amountMs: number) => Promise<void>;
  beginScrub: () => void;
  previewScrub: (positionMs: SongTimeMs) => void;
  commitScrub: (positionMs: SongTimeMs) => Promise<void>;
} {
  const [timeline] = useState(() => new KaraokeTimeline(new ExpoInstrumentalPlayback()));
  const [lyricTimeline] = useState(() => new LyricTimeline(song));
  const [actionError, setActionError] = useState<string | null>(null);
  const [scrubPositionMs, setScrubPositionMs] = useState<SongTimeMs | null>(null);
  const resumeAfterScrubRef = useRef(false);
  const snapshot = useKaraokeTimeline(timeline);
  const displayPositionMs = scrubPositionMs ?? snapshot.positionMs;
  // This anticipates the visual cue only. Playback and future analysis stay on song time.
  const lyricDisplayPositionMs = clampSongTime(
    displayPositionMs + LYRIC_DISPLAY_LEAD_MS,
    song.metadata.durationMs,
  );

  useEffect(() => {
    let isCurrent = true;

    void timeline.load(song).catch((error: unknown) => {
      if (isCurrent) {
        setActionError(messageFromError(error, "Could not load the instrumental."));
      }
    });

    return () => {
      isCurrent = false;
      void timeline.dispose();
    };
  }, [song, timeline]);

  return {
    snapshot: { ...snapshot, positionMs: displayPositionMs },
    lyrics: lyricTimeline.lookup(lyricDisplayPositionMs),
    expectedNote: findExpectedNote(song.melody.notes, displayPositionMs),
    error: snapshot.error ?? actionError,
    play: () => runTimelineAction(() => timeline.play(), setActionError),
    pause: () => runTimelineAction(() => timeline.pause(), setActionError),
    restart: () => runTimelineAction(() => timeline.restart(), setActionError),
    retry: () => runTimelineAction(() => timeline.load(song), setActionError),
    seekBy: (amountMs) => {
      const targetMs = clampSongTime(snapshot.positionMs + amountMs, song.metadata.durationMs);
      return runTimelineAction(() => timeline.seekTo(targetMs), setActionError);
    },
    beginScrub: () => {
      resumeAfterScrubRef.current = snapshot.state === "playing";
      setScrubPositionMs(snapshot.positionMs);
      if (resumeAfterScrubRef.current) {
        void runTimelineAction(() => timeline.pause(), setActionError);
      }
    },
    previewScrub: (positionMs) => setScrubPositionMs(clampSongTime(positionMs, song.metadata.durationMs)),
    commitScrub: async (positionMs) => {
      const targetMs = clampSongTime(positionMs, song.metadata.durationMs);
      await runTimelineAction(() => timeline.seekTo(targetMs), setActionError);
      setScrubPositionMs(null);
      if (resumeAfterScrubRef.current) {
        resumeAfterScrubRef.current = false;
        await runTimelineAction(() => timeline.play(), setActionError);
      }
    },
  };
}

export { SEEK_STEP_MS };

async function runTimelineAction(
  action: () => Promise<unknown>,
  setActionError: (error: string | null) => void,
): Promise<void> {
  setActionError(null);
  try {
    await action();
  } catch (error) {
    setActionError(messageFromError(error, "Could not update playback."));
  }
}

function clampSongTime(value: number, durationMs: SongTimeMs): SongTimeMs {
  return Math.round(Math.min(Math.max(value, 0), durationMs)) as SongTimeMs;
}

function findExpectedNote(notes: readonly ExpectedNote[], currentTimeMs: SongTimeMs): ExpectedNote | null {
  let low = 0;
  let high = notes.length - 1;
  let candidateIndex = -1;

  while (low <= high) {
    const midpoint = Math.floor((low + high) / 2);
    if (notes[midpoint].startMs <= currentTimeMs) {
      candidateIndex = midpoint;
      low = midpoint + 1;
    } else {
      high = midpoint - 1;
    }
  }

  if (candidateIndex === -1) {
    return null;
  }

  const note = notes[candidateIndex];
  return currentTimeMs < note.endMs ? note : null;
}

function messageFromError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
