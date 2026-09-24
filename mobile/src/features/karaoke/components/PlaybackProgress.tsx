import { LinearGradient } from "expo-linear-gradient";
import { StyleSheet, Text, View } from "react-native";

import type { SongTimeMs } from "@/features/songs/types";

type PlaybackProgressProps = {
  positionMs: SongTimeMs;
  durationMs: SongTimeMs | null;
};

export function PlaybackProgress({ positionMs, durationMs }: PlaybackProgressProps) {
  const progress = durationMs === null || durationMs === 0 ? 0 : Math.min(positionMs / durationMs, 1);

  return (
    <View className="gap-2 px-8" style={styles.root}>
      <View className="h-[2px] overflow-hidden rounded-full bg-[#46324f]" style={styles.track}>
        <LinearGradient className="h-full rounded-full" colors={["#f47ccc", "#e8fa57"]} style={[styles.fill, { width: `${progress * 100}%` }]} />
      </View>
      <View className="flex-row justify-between" style={styles.labels}>
        <Text className="text-xs font-bold text-[#a99aaf]" style={styles.label}>{formatTime(positionMs)}</Text>
        <Text className="text-xs font-bold text-[#a99aaf]" style={styles.label}>{durationMs === null ? "--:--" : formatTime(durationMs)}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { gap: 8, paddingHorizontal: 32 },
  track: { height: 2, overflow: "hidden", borderRadius: 1, backgroundColor: "#46324f" },
  fill: { height: "100%", borderRadius: 1 },
  labels: { flexDirection: "row", justifyContent: "space-between" },
  label: { color: "#a99aaf", fontSize: 12, fontWeight: "700" },
});

function formatTime(milliseconds: SongTimeMs): string {
  const totalSeconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}
