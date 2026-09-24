import { Text, View } from "react-native";

import type { LyricLookup } from "@/features/lyrics";
import type { PlaybackState } from "@/features/playback/types";

import { LyricStage } from "./LyricStage";

type PerformanceStageProps = {
  lookup: LyricLookup;
  playbackState: PlaybackState;
};

export function PerformanceStage({ lookup, playbackState }: PerformanceStageProps) {
  return (
    <View className="flex-1">
      <View className="items-center pt-5">
        <Text className="text-[10px] font-extrabold uppercase tracking-[3px] text-[#e8fa57]">
          {playbackState === "paused" ? "Paused" : playbackState === "ended" ? "Finished" : "Sing it"}
        </Text>
      </View>
      <LyricStage lookup={lookup} playbackState={playbackState} />
    </View>
  );
}
