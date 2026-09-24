import { LinearGradient } from "expo-linear-gradient";
import { type GestureResponderEvent, StyleSheet, Text, View } from "react-native";
import { useState } from "react";

import type { SongTimeMs } from "@/features/songs/types";

type PlaybackProgressProps = {
  positionMs: SongTimeMs;
  durationMs: SongTimeMs | null;
  disabled: boolean;
  onScrubStart: () => void;
  onScrub: (positionMs: SongTimeMs) => void;
  onScrubEnd: (positionMs: SongTimeMs) => void;
};

export function PlaybackProgress({ positionMs, durationMs, disabled, onScrubStart, onScrub, onScrubEnd }: PlaybackProgressProps) {
  const progress = durationMs === null || durationMs === 0 ? 0 : Math.min(positionMs / durationMs, 1);
  const [trackWidth, setTrackWidth] = useState(0);
  const resolvePosition = (event: GestureResponderEvent): SongTimeMs => {
    const ratio = trackWidth ? Math.min(Math.max(event.nativeEvent.locationX / trackWidth, 0), 1) : progress;
    return Math.round(ratio * (durationMs ?? 0)) as SongTimeMs;
  };

  return (
    <View style={styles.root}>
      <View
        accessibilityRole="adjustable"
        accessible
        style={styles.hitArea}
        onResponderGrant={(event) => { onScrubStart(); onScrub(resolvePosition(event)); }}
        onResponderMove={(event) => onScrub(resolvePosition(event))}
        onResponderRelease={(event) => onScrubEnd(resolvePosition(event))}
        onStartShouldSetResponder={() => !disabled && durationMs !== null}
        onLayout={(event) => setTrackWidth(event.nativeEvent.layout.width)}
      >
      <View style={styles.track}>
        <LinearGradient colors={["#f47ccc", "#e8fa57"]} style={[styles.fill, { width: `${progress * 100}%` }]} />
        <View style={[styles.thumb, { left: `${progress * 100}%` }]} />
      </View>
      </View>
      <View style={styles.labels}>
        <Text style={styles.label}>{formatTime(positionMs)}</Text>
        <Text style={styles.label}>{durationMs === null ? "--:--" : formatTime(durationMs)}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { gap: 5, paddingHorizontal: 32 },
  hitArea: { height: 30, justifyContent: "center" },
  track: { height: 2, overflow: "hidden", borderRadius: 1, backgroundColor: "#46324f" },
  fill: { height: "100%", borderRadius: 1 },
  thumb: { position: "absolute", top: -5, width: 12, height: 12, borderRadius: 6, backgroundColor: "#d98ae8", transform: [{ translateX: -6 }] },
  labels: { flexDirection: "row", justifyContent: "space-between" },
  label: { color: "#a99aaf", fontSize: 12, fontWeight: "700" },
});

function formatTime(milliseconds: SongTimeMs): string {
  const totalSeconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}
