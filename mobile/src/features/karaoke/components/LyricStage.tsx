import { StyleSheet, Text, View } from "react-native";

import type { LyricLookup } from "@/features/lyrics";

type LyricStageProps = {
  lookup: LyricLookup;
};

export function LyricStage({ lookup }: LyricStageProps) {
  return (
    <View style={styles.root}>
      {lookup.activeLine ? <Text numberOfLines={2} style={styles.context}>{lookup.previousLine?.text ?? " "}</Text> : null}
      {lookup.activeLine ? (
        <Text style={styles.activeLine}>
          {lookup.activeLine.segments.map((segment, index) => (
            <Text
              key={segment.id}
              style={segment.id === lookup.activeWord?.id ? styles.activeWord : styles.inactiveWord}
            >
              {`${index === 0 ? "" : " "}${segment.text}`}
            </Text>
          ))}
        </Text>
      ) : null}
      {lookup.activeLine ? <Text numberOfLines={2} style={styles.context}>{lookup.nextLine?.text ?? " "}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { minHeight: 250, flex: 1, justifyContent: "center", paddingHorizontal: 28 },
  context: { color: "#9b8ba3", fontSize: 16, lineHeight: 24, textAlign: "center", marginVertical: 16, opacity: 0.62 },
  activeLine: { color: "#f8f2ff", fontSize: 32, lineHeight: 42, fontWeight: "800", textAlign: "center" },
  activeWord: { color: "#e8fa57", fontWeight: "800", textDecorationLine: "underline" },
  inactiveWord: { color: "#f8f2ff" },
});
