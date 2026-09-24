import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { useRouter } from "expo-router";

import { songCatalog, SongPackageError } from "@/features/songs/catalog";
import type { KaraokeSong, SongId } from "@/features/songs/types";

import { ExpectedNoteDebug } from "./components/ExpectedNoteDebug";
import { AmbientStageBackground } from "./components/AmbientStageBackground";
import { NowPlayingIntro } from "./components/NowPlayingIntro";
import { PerformanceStage } from "./components/PerformanceStage";
import { PlaybackProgress } from "./components/PlaybackProgress";
import { TransportControls } from "./components/TransportControls";
import { SEEK_STEP_MS, useKaraokeSession } from "./useKaraokeSession";

type KaraokeSessionScreenProps = {
  songId: SongId | undefined;
};

export function KaraokeSessionScreen({ songId }: KaraokeSessionScreenProps) {
  if (!songId) {
    return <UnavailableSongScreen message="This karaoke route has no song ID." />;
  }

  const songResult = getSong(songId);
  if (!songResult.ok) {
    return <UnavailableSongScreen message={songResult.message} />;
  }

  return <LoadedKaraokeSession key={songResult.song.metadata.id} song={songResult.song} />;
}

function getSong(songId: SongId): { ok: true; song: KaraokeSong } | { ok: false; message: string } {
  try {
    return { ok: true, song: songCatalog.getSong(songId) };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof SongPackageError ? error.message : "This prepared song is unavailable.",
    };
  }
}

function LoadedKaraokeSession({ song }: { song: KaraokeSong }) {
  const router = useRouter();
  const session = useKaraokeSession(song);
  const isLoading = session.snapshot.state === "idle" || session.snapshot.state === "loading";
  const isError = session.snapshot.state === "error";

  return (
    <SafeAreaView className="relative flex-1 overflow-hidden bg-[#0a0910]" style={styles.safeArea}>
      <StatusBar style="light" />
      <AmbientStageBackground variant="player" />
      <View className="flex-1">
        <View className="flex-row items-center justify-between px-6 pt-3" style={styles.header}>
          <Pressable accessibilityRole="button" className="h-9 w-9 items-center justify-center rounded-full bg-[#ffffff]/15" onPress={() => router.replace("/")} style={styles.headerButton}>
            <Text className="text-sm font-extrabold text-[#f8f2ff]" style={styles.headerButtonLabel}>Back</Text>
          </Pressable>
          <Text className="text-xs font-extrabold text-[#f8f2ff]" style={styles.headerTitle}>Now Playing</Text>
          <View className="h-9 w-9 items-center justify-center rounded-full bg-[#ffffff]/15" style={styles.headerButton}>
            <Text className="text-[9px] font-extrabold text-[#f8f2ff]" style={styles.headerButtonLabel}>ON</Text>
          </View>
        </View>

        {isLoading ? (
          <LoadingStage />
        ) : isError ? null : session.snapshot.state === "ready" ? (
          <NowPlayingIntro song={song} onStart={() => void session.play()} />
        ) : (
          <>
            <View className="px-6 pt-3">
              <Text className="text-xl font-extrabold text-[#f8f2ff]" numberOfLines={1}>{song.metadata.title}</Text>
              <Text className="mt-1 text-sm font-medium text-[#b9aaba]">{song.metadata.primaryArtist}</Text>
            </View>
            <PerformanceStage lookup={session.lyrics} playbackState={session.snapshot.state} />
          </>
        )}

        {__DEV__ ? <ExpectedNoteDebug note={session.expectedNote} /> : null}
        <PlaybackProgress positionMs={session.snapshot.positionMs} durationMs={session.snapshot.durationMs} />

        <View className="gap-4 px-0 pb-5 pt-5">
          {isError ? (
            <ErrorControls error={session.error ?? "Could not prepare the instrumental."} onRetry={() => void session.retry()} />
          ) : (
            <>
              {session.snapshot.state === "ready" ? null : (
                <TransportControls
                  state={session.snapshot.state}
                  onPause={() => void session.pause()}
                  onPlay={() => void session.play()}
                  onRestart={() => void session.restart()}
                  onSeekBackward={() => void session.seekBy(-SEEK_STEP_MS)}
                  onSeekForward={() => void session.seekBy(SEEK_STEP_MS)}
                />
              )}
            </>
          )}
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, position: "relative", overflow: "hidden", backgroundColor: "#0a0910" },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 24, paddingTop: 12 },
  headerButton: { width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center", backgroundColor: "rgba(255,255,255,0.15)" },
  headerButtonLabel: { color: "#f8f2ff", fontSize: 9, fontWeight: "800" },
  headerTitle: { color: "#f8f2ff", fontSize: 12, fontWeight: "800" },
});

function LoadingStage() {
  return (
    <View className="min-h-[250px] flex-1 items-center justify-center px-6">
      <Text className="text-xl font-extrabold text-[#f8f2ff]">Preparing instrumental...</Text>
      <Text className="mt-2 text-center text-base text-[#c6b5ca]">Lyrics will follow the actual playback position.</Text>
    </View>
  );
}

function ErrorControls({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <View className="items-center gap-4 px-6">
      <Text className="text-center text-sm leading-5 text-[#f0a3d7]">{error}</Text>
      <Pressable accessibilityRole="button" className="min-h-12 items-center justify-center rounded-full bg-[#f47ccc] px-6" onPress={onRetry}>
        <Text className="font-extrabold text-[#24112b]">Retry</Text>
      </Pressable>
    </View>
  );
}

function UnavailableSongScreen({ message }: { message: string }) {
  const router = useRouter();

  return (
    <SafeAreaView className="flex-1 items-center justify-center bg-[#09070f] px-8">
      <StatusBar style="light" />
      <Text className="text-center text-2xl font-extrabold text-[#f8f2ff]">Song unavailable</Text>
      <Text className="mt-3 text-center text-base leading-6 text-[#c6b5ca]">{message}</Text>
      <Pressable accessibilityRole="button" className="mt-7 min-h-12 justify-center rounded-full bg-[#f47ccc] px-6" onPress={() => router.replace("/")}>
        <Text className="font-extrabold text-[#24112b]">Back to library</Text>
      </Pressable>
    </SafeAreaView>
  );
}
