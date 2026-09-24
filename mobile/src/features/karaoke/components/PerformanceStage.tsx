import { Animated, StyleSheet, Text, View } from "react-native";
import { useEffect, useState } from "react";

import type { LyricLookup } from "@/features/lyrics";
import type { PlaybackState } from "@/features/playback/types";

import { LyricStage } from "./LyricStage";

type PerformanceStageProps = {
  lookup: LyricLookup;
  playbackState: PlaybackState;
};

export function PerformanceStage({ lookup, playbackState }: PerformanceStageProps) {
  const [opacity] = useState(() => new Animated.Value(0));
  const [translateY] = useState(() => new Animated.Value(12));

  useEffect(() => {
    Animated.parallel([
      Animated.timing(opacity, { toValue: 1, duration: 220, useNativeDriver: true }),
      Animated.timing(translateY, { toValue: 0, duration: 220, useNativeDriver: true }),
    ]).start();
  }, [opacity, translateY]);

  return (
    <Animated.View style={[styles.root, { opacity, transform: [{ translateY }] }]}>
      <View style={styles.status}>
        <Text style={styles.statusText}>
          {playbackState === "paused" ? "Paused" : playbackState === "ended" ? "Finished" : "Sing it"}
        </Text>
      </View>
      <LyricStage lookup={lookup} />
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  status: { alignItems: "center", paddingTop: 20 },
  statusText: { color: "#ffffff", fontSize: 10, fontWeight: "800", letterSpacing: 3, opacity: 0.7, textTransform: "uppercase" },
});
