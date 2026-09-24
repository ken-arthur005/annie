import { LinearGradient } from "expo-linear-gradient";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";

import type { KaraokeSong } from "@/features/songs/types";

type NowPlayingIntroProps = {
  song: KaraokeSong;
  onStart: () => void;
};

export function NowPlayingIntro({ song, onStart }: NowPlayingIntroProps) {
  return (
    <View className="flex-1 items-center justify-center px-8 pb-3" style={styles.root}>
      <LinearGradient
        className="mb-6 h-52 w-52 items-center justify-center rounded-full p-1"
        colors={["#f38bcf", "#ce7ce9", "#9f69d3"]}
        locations={[0, 0.55, 1]}
        start={{ x: 0.1, y: 0 }}
        end={{ x: 0.88, y: 1 }}
        style={styles.artworkRing}
      >
        {song.artwork ? (
          <Image className="h-full w-full rounded-full" source={song.artwork} style={styles.artwork} />
        ) : (
          <View className="h-full w-full items-center justify-center rounded-full bg-[#211329]">
            <Text className="text-xl font-extrabold uppercase tracking-[4px] text-[#e8fa57]">Annie</Text>
          </View>
        )}
      </LinearGradient>
      <Text className="text-center text-2xl font-extrabold leading-8 text-[#f8f2ff]" style={styles.title}>{song.metadata.title}</Text>
      <Text className="mt-1 text-center text-sm font-medium text-[#b9aaba]" style={styles.artist}>{song.metadata.primaryArtist}</Text>
      <Text className="mt-7 text-center text-xs font-bold uppercase tracking-[2px] text-[#e8fa57]" style={styles.ready}>Ready when you are</Text>
      <Pressable
        accessibilityRole="button"
        className="mt-4 min-h-14 min-w-52 items-center justify-center rounded-full bg-[#f47ccc] px-7 active:bg-[#dc62b8]"
        onPress={onStart}
        style={styles.startButton}
      >
        <Text className="text-base font-extrabold text-[#24112b]" style={styles.startLabel}>Start karaoke</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: 32, paddingBottom: 12 },
  artworkRing: { width: 182, height: 182, borderRadius: 91, alignItems: "center", justifyContent: "center", padding: 3, marginBottom: 24 },
  artwork: { width: "100%", height: "100%", borderRadius: 88 },
  title: { color: "#f8f2ff", fontSize: 24, lineHeight: 30, fontWeight: "800", textAlign: "center" },
  artist: { marginTop: 4, color: "#b9aaba", fontSize: 14, fontWeight: "500", textAlign: "center" },
  ready: { marginTop: 28, color: "#e8fa57", fontSize: 12, fontWeight: "700", letterSpacing: 2, textTransform: "uppercase", textAlign: "center" },
  startButton: { marginTop: 16, minHeight: 56, minWidth: 208, alignItems: "center", justifyContent: "center", borderRadius: 28, paddingHorizontal: 28, backgroundColor: "#f47ccc" },
  startLabel: { color: "#24112b", fontSize: 16, fontWeight: "800" },
});
