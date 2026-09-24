import { StyleSheet, Text, View } from "react-native";

import type { LyricLookup } from "@/features/lyrics";
import type { PlaybackState } from "@/features/playback/types";

type LyricStageProps = {
  lookup: LyricLookup;
  playbackState: PlaybackState;
};

export function LyricStage({ lookup, playbackState }: LyricStageProps) {
  const centralMessage = playbackState === "ended" ? "Instrumental complete" : "Listen for the next line";

  return (
    <View className="min-h-[250px] flex-1 justify-center px-7" style={styles.root}>
      <Text className="mb-7 text-center text-base leading-6 text-[#9b8ba3]" numberOfLines={2} style={styles.context}>
        {lookup.previousLine?.text ?? " "}
      </Text>
      {lookup.activeLine ? (
        <Text className="text-center text-[32px] font-extrabold leading-[42px] text-[#f8f2ff]" style={styles.activeLine}>
          {lookup.activeLine.segments.map((segment, index) => (
            <Text
              key={segment.id}
              className={segment.id === lookup.activeWord?.id ? "text-[#e8fa57] underline" : "text-[#f8f2ff]"}
              style={segment.id === lookup.activeWord?.id ? styles.activeWord : styles.inactiveWord}
            >
              {`${index === 0 ? "" : " "}${segment.text}`}
            </Text>
          ))}
        </Text>
      ) : (
        <Text className="text-center text-[26px] font-bold leading-9 text-[#d9ccdf]" style={styles.empty}>{centralMessage}</Text>
      )}
      <Text className="mt-7 text-center text-base leading-6 text-[#9b8ba3]" numberOfLines={2} style={styles.context}>
        {lookup.nextLine?.text ?? " "}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { minHeight: 250, flex: 1, justifyContent: "center", paddingHorizontal: 28 },
  context: { color: "#9b8ba3", fontSize: 16, lineHeight: 24, textAlign: "center", marginVertical: 12, opacity: 0.62 },
  activeLine: { color: "#f8f2ff", fontSize: 32, lineHeight: 42, fontWeight: "800", textAlign: "center" },
  activeWord: { color: "#e8fa57", fontWeight: "800", textDecorationLine: "underline" },
  inactiveWord: { color: "#f8f2ff" },
  empty: { color: "#d9ccdf", fontSize: 26, lineHeight: 36, fontWeight: "700", textAlign: "center" },
});
