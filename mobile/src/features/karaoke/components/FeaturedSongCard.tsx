import { LinearGradient } from "expo-linear-gradient";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";

import type { SongSummary } from "@/features/songs/types";

type FeaturedSongCardProps = {
  song: SongSummary;
  onPress: () => void;
};

export function FeaturedSongCard({ song, onPress }: FeaturedSongCardProps) {
  return (
    <Pressable accessibilityRole="button" className="overflow-hidden rounded-[24px] active:opacity-90" onPress={onPress} style={styles.pressable}>
      <LinearGradient
        className="h-32 overflow-hidden px-4 py-4"
        colors={["#fa94d9", "#de82ee", "#c274e7"]}
        locations={[0, 0.55, 1]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.card}
      >
        <View className="max-w-[57%] gap-1" style={styles.copy}>
          <Text className="text-[9px] font-extrabold uppercase tracking-[1.5px] text-[#4b1d4b]" style={styles.eyebrow}>Prepared tonight</Text>
          <Text className="text-lg font-extrabold leading-5 text-[#211126]" style={styles.title}>{song.title}</Text>
          <Text className="text-xs font-bold text-[#552755]" style={styles.artist}>{song.artist}</Text>
        </View>
        <View className="absolute bottom-4 left-4 h-9 w-9 items-center justify-center rounded-full bg-[#25122e]" style={styles.playButton}>
          <Text className="ml-0.5 text-xs font-extrabold text-[#f8f2ff]" style={styles.playLabel}>{">"}</Text>
        </View>
        {song.artwork ? (
          <Image className="absolute -right-2 -top-2 h-36 w-36 rounded-bl-[52px]" source={song.artwork} style={styles.artwork} />
        ) : (
          <View className="absolute -right-2 -top-2 h-36 w-36 items-center justify-center rounded-bl-[52px] bg-[#3a1748]">
            <Text className="text-sm font-extrabold uppercase tracking-[3px] text-[#e8fa57]">Annie</Text>
          </View>
        )}
      </LinearGradient>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  pressable: { overflow: "hidden", borderRadius: 24 },
  card: { height: 112, overflow: "hidden", padding: 14 },
  copy: { maxWidth: "57%", gap: 3 },
  eyebrow: { color: "#4b1d4b", fontSize: 9, fontWeight: "800", letterSpacing: 1.5, textTransform: "uppercase" },
  title: { color: "#211126", fontSize: 18, fontWeight: "800", lineHeight: 20 },
  artist: { color: "#552755", fontSize: 12, fontWeight: "700" },
  playButton: { position: "absolute", left: 14, bottom: 14, width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", backgroundColor: "#25122e" },
  playLabel: { color: "#f8f2ff", fontSize: 14, fontWeight: "800", marginLeft: 2 },
  artwork: { position: "absolute", right: -7, top: -7, width: 126, height: 126, borderBottomLeftRadius: 52 },
});
