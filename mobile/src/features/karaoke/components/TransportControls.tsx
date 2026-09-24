import { Pressable, StyleSheet, Text, View } from "react-native";

import type { PlaybackState } from "@/features/playback/types";

type Props = { state: PlaybackState; onPlay: () => void; onPause: () => void; onRestart: () => void; onSeekBackward: () => void; onSeekForward: () => void };

export function TransportControls({ state, onPlay, onPause, onRestart, onSeekBackward, onSeekForward }: Props) {
  const disabled = state === "idle" || state === "loading" || state === "error";
  const primary = state === "playing" ? onPause : onPlay;
  return <View style={styles.row}>
    <Control label="R" onPress={onRestart} disabled={disabled} />
    <Control label="-5" onPress={onSeekBackward} disabled={disabled} />
    <Pressable accessibilityRole="button" disabled={disabled} onPress={primary} style={({ pressed }) => [styles.primary, pressed && styles.pressed, disabled && styles.disabled]}><Text style={styles.primaryLabel}>{state === "playing" ? "Pause" : state === "ended" ? "Replay" : "Play"}</Text></Pressable>
    <Control label="+5" onPress={onSeekForward} disabled={disabled} />
  </View>;
}

function Control({ label, onPress, disabled }: { label: string; onPress: () => void; disabled: boolean }) {
  return <Pressable accessibilityRole="button" disabled={disabled} onPress={onPress} style={({ pressed }) => [styles.secondary, pressed && styles.pressed, disabled && styles.disabled]}><Text style={styles.secondaryLabel}>{label}</Text></Pressable>;
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 14, paddingHorizontal: 24 },
  secondary: { width: 44, height: 44, borderRadius: 22, alignItems: "center", justifyContent: "center", backgroundColor: "#2a1b33" },
  secondaryLabel: { color: "#ffffff", fontSize: 11, fontWeight: "800" },
  primary: { width: 64, height: 64, borderRadius: 32, alignItems: "center", justifyContent: "center", backgroundColor: "#d98ae8" },
  primaryLabel: { color: "#ffffff", fontSize: 12, fontWeight: "800" },
  pressed: { transform: [{ scale: 0.95 }], opacity: 0.86 },
  disabled: { opacity: 0.4 },
});
