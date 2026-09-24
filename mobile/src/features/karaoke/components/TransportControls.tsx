import { Pressable, Text, View } from "react-native";

import type { PlaybackState } from "@/features/playback/types";

type TransportControlsProps = {
  state: PlaybackState;
  onPlay: () => void;
  onPause: () => void;
  onRestart: () => void;
  onSeekBackward: () => void;
  onSeekForward: () => void;
};

export function TransportControls({ state, onPlay, onPause, onRestart, onSeekBackward, onSeekForward }: TransportControlsProps) {
  const isLoading = state === "idle" || state === "loading";
  const isPlaying = state === "playing";
  const isEnded = state === "ended";

  return (
    <View className="flex-row items-center justify-center gap-3 px-6">
      <Pressable
        accessibilityRole="button"
        className="h-11 w-11 items-center justify-center rounded-full bg-[#2a1b33] active:bg-[#38203d] disabled:opacity-40"
        disabled={isLoading || state === "error"}
        onPress={onRestart}
      >
        <Text className="text-[10px] font-extrabold text-[#f8f2ff]">R</Text>
      </Pressable>
      <Pressable
        accessibilityRole="button"
        className="h-11 w-11 items-center justify-center rounded-full bg-[#2a1b33] active:bg-[#38203d] disabled:opacity-40"
        disabled={isLoading || state === "error"}
        onPress={onSeekBackward}
      >
        <Text className="text-[10px] font-extrabold text-[#f8f2ff]">-5</Text>
      </Pressable>
      <Pressable
        accessibilityRole="button"
        className="h-16 w-16 items-center justify-center rounded-full bg-[#d98ae8] active:bg-[#c66ed9] disabled:opacity-40"
        disabled={isLoading || state === "error"}
        onPress={isPlaying ? onPause : onPlay}
      >
        <Text className="text-xs font-extrabold text-[#24112b]">
          {isLoading ? "..." : isPlaying ? "Pause" : isEnded ? "Replay" : "Play"}
        </Text>
      </Pressable>
      <Pressable
        accessibilityRole="button"
        className="h-11 w-11 items-center justify-center rounded-full bg-[#2a1b33] active:bg-[#38203d] disabled:opacity-40"
        disabled={isLoading || state === "error"}
        onPress={onSeekForward}
      >
        <Text className="text-[10px] font-extrabold text-[#f8f2ff]">+5</Text>
      </Pressable>
    </View>
  );
}
