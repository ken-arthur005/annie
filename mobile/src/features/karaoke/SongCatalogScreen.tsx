import { Image, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { useRouter } from "expo-router";

import { songCatalog } from "@/features/songs/catalog";
import type { SongSummary } from "@/features/songs/types";

import { AmbientStageBackground } from "./components/AmbientStageBackground";
import { FeaturedSongCard } from "./components/FeaturedSongCard";

export function SongCatalogScreen() {
  const router = useRouter();
  const songs = songCatalog.listSongs();
  const loadErrors = songCatalog.getLoadErrors();

  return (
    <SafeAreaView className="relative flex-1 overflow-hidden bg-[#0a0910]" style={styles.safeArea}>
      <StatusBar style="light" />
      <AmbientStageBackground variant="catalog" />
      <ScrollView contentContainerStyle={styles.content}>
        <View className="mb-6 flex-row items-center justify-between" style={styles.topRow}>
          <View className="h-10 w-10 items-center justify-center rounded-full border border-[#fa94d9] bg-[#3b1c4a]" style={styles.avatar}>
            <Text className="text-xs font-extrabold text-[#f8f2ff]" style={styles.avatarText}>A</Text>
          </View>
          <View className="flex-row gap-2" style={styles.statusRow}>
            <View className="h-9 w-9 items-center justify-center rounded-full bg-[#24202e]" style={styles.statusDot}>
              <Text className="text-[10px] font-extrabold text-[#f8f2ff]" style={styles.statusText}>1</Text>
            </View>
            <View className="h-9 w-9 items-center justify-center rounded-full bg-[#24202e]" style={styles.statusDot}>
              <Text className="text-[9px] font-extrabold text-[#f8f2ff]" style={styles.statusText}>ON</Text>
            </View>
          </View>
        </View>

        <View className="mb-6 gap-3" style={styles.hero}>
          <Text className="text-[28px] font-extrabold tracking-tight text-[#f8f2ff]" style={styles.heading}>Annie</Text>
          <Text className="max-w-[78%] text-base font-medium leading-6 text-[#c6b5ca]" style={styles.tagline}>Prepared tracks, timed lyrics, and a clear stage.</Text>
        </View>

        <Text className="mb-3 text-lg font-extrabold text-[#f8f2ff]" style={styles.sectionTitle}>Featured tonight</Text>
        {songs[0] ? <FeaturedSongCard song={songs[0]} onPress={() => openSong(router, songs[0])} /> : null}

        <View className="mb-3 mt-7 flex-row items-end justify-between" style={styles.sectionRow}>
          <Text className="text-lg font-extrabold text-[#f8f2ff]" style={styles.sectionTitle}>Choose a song</Text>
          <Text className="text-xs font-bold text-[#b9aaba]" style={styles.count}>{songs.length} prepared</Text>
        </View>

        <View className="gap-3">
          {songs.map((song) => (
            <SongCatalogListItem key={song.id} song={song} />
          ))}
        </View>

        {songs.length === 0 ? (
          <View className="flex-1 justify-center py-20">
            <Text className="text-xl font-bold text-[#f8f2ff]">No prepared songs are available.</Text>
            <Text className="mt-2 text-base text-[#c6b5ca]">Add a validated runtime song package to continue.</Text>
          </View>
        ) : null}

        {loadErrors.length > 0 ? (
          <Text className="mt-8 text-sm leading-5 text-[#f0a3d7]">
            Some prepared songs could not be loaded. Check the runtime song package validation output.
          </Text>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function SongCatalogListItem({ song }: { song: SongSummary }) {
  const router = useRouter();

  return (
    <Pressable
      accessibilityRole="button"
      className="min-h-20 flex-row-reverse items-center gap-3 border-b border-[#36263e] py-3 active:opacity-70"
      onPress={() => openSong(router, song)}
      style={styles.songRow}
    >
      {song.artwork ? (
        <Image className="h-16 w-16 rounded-2xl bg-[#392342]" source={song.artwork} style={styles.songArtwork} />
      ) : (
        <View className="h-16 w-16 items-center justify-center rounded-2xl bg-[#392342]" style={styles.songArtwork}>
          <Text className="text-xs font-extrabold uppercase tracking-[2px] text-[#e8fa57]">Sing</Text>
        </View>
      )}
      <View className="flex-1 gap-1" style={styles.songCopy}>
        <Text className="text-base font-extrabold text-[#f8f2ff]" style={styles.songTitle}>{song.title}</Text>
        <Text className="text-xs font-medium text-[#c6b5ca]" style={styles.songMeta}>{song.artist}  •  {formatDuration(song.durationMs)}</Text>
        <Text className="text-[10px] font-bold uppercase tracking-wider text-[#9e8ba5]" style={styles.songPrepared}>Prepared track</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, position: "relative", overflow: "hidden", backgroundColor: "#0a0910" },
  content: { flexGrow: 1, paddingHorizontal: 20, paddingTop: 12, paddingBottom: 40 },
  topRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 24 },
  avatar: { width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: "#fa94d9", backgroundColor: "#3b1c4a" },
  avatarText: { color: "#f8f2ff", fontSize: 12, fontWeight: "800" },
  statusRow: { flexDirection: "row", gap: 8 },
  statusDot: { width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", backgroundColor: "#24202e" },
  statusText: { color: "#f8f2ff", fontSize: 10, fontWeight: "800" },
  hero: { marginBottom: 24, gap: 10 },
  heading: { color: "#f8f2ff", fontSize: 28, fontWeight: "800", letterSpacing: -0.5 },
  tagline: { maxWidth: "78%", color: "#c6b5ca", fontSize: 16, lineHeight: 24, fontWeight: "500" },
  sectionTitle: { color: "#f8f2ff", fontSize: 18, fontWeight: "800" },
  sectionRow: { flexDirection: "row", alignItems: "flex-end", justifyContent: "space-between", marginTop: 28, marginBottom: 12 },
  count: { color: "#b9aaba", fontSize: 12, fontWeight: "700" },
  songRow: { minHeight: 80, flexDirection: "row-reverse", alignItems: "center", gap: 12, borderBottomWidth: 1, borderColor: "#36263e", paddingVertical: 12 },
  songArtwork: { width: 64, height: 64, borderRadius: 16, backgroundColor: "#392342" },
  songCopy: { flex: 1, gap: 3 },
  songTitle: { color: "#f8f2ff", fontSize: 16, fontWeight: "800" },
  songMeta: { color: "#c6b5ca", fontSize: 12, fontWeight: "500" },
  songPrepared: { color: "#9e8ba5", fontSize: 10, fontWeight: "700", letterSpacing: 0.6, textTransform: "uppercase" },
});

function openSong(router: ReturnType<typeof useRouter>, song: SongSummary): void {
  router.push({ pathname: "/karaoke/[songId]", params: { songId: song.id } });
}

function formatDuration(milliseconds: number): string {
  const totalSeconds = Math.floor(milliseconds / 1000);
  return `${Math.floor(totalSeconds / 60)}:${(totalSeconds % 60).toString().padStart(2, "0")}`;
}
