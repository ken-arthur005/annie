import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { useRouter } from "expo-router";

import { songCatalog, SongPackageError } from "@/features/songs/catalog";
import type { KaraokeSong, SongId } from "@/features/songs/types";

import { AmbientStageBackground } from "./components/AmbientStageBackground";
import { NowPlayingIntro } from "./components/NowPlayingIntro";
import { PerformanceStage } from "./components/PerformanceStage";
import { PlaybackProgress } from "./components/PlaybackProgress";
import { TransportControls } from "./components/TransportControls";
import { SEEK_STEP_MS, useKaraokeSession } from "./useKaraokeSession";

type KaraokeSessionScreenProps = { songId: SongId | undefined };

export function KaraokeSessionScreen({ songId }: KaraokeSessionScreenProps) {
  if (!songId) return <UnavailableSongScreen message="This karaoke route has no song ID." />;

  const songResult = getSong(songId);
  if (!songResult.ok) return <UnavailableSongScreen message={songResult.message} />;

  return <LoadedKaraokeSession key={songResult.song.metadata.id} song={songResult.song} />;
}

function getSong(songId: SongId): { ok: true; song: KaraokeSong } | { ok: false; message: string } {
  try {
    return { ok: true, song: songCatalog.getSong(songId) };
  } catch (error) {
    return { ok: false, message: error instanceof SongPackageError ? error.message : "This prepared song is unavailable." };
  }
}

function LoadedKaraokeSession({ song }: { song: KaraokeSong }) {
  const router = useRouter();
  const session = useKaraokeSession(song);
  const isLoading = session.snapshot.state === "idle" || session.snapshot.state === "loading";
  const isError = session.snapshot.state === "error";

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />
      <AmbientStageBackground variant="player" />
      <View style={styles.screen}>
        <View style={styles.header}>
          <Pressable accessibilityRole="button" onPress={() => router.replace("/")} style={styles.headerButton}>
            <Text style={styles.headerButtonLabel}>Back</Text>
          </Pressable>
          <View style={styles.trackInfo}>
            <Text numberOfLines={1} style={styles.trackTitle}>{song.metadata.title}</Text>
            <Text numberOfLines={1} style={styles.trackArtist}>{song.metadata.primaryArtist}</Text>
            <Text style={styles.nowPlaying}>Now Playing</Text>
          </View>
        </View>

        <View style={styles.lyricRegion}>
          {isLoading ? <LoadingStage /> : isError ? null : session.snapshot.state === "ready" ? (
            <NowPlayingIntro song={song} onStart={() => void session.play()} />
          ) : <PerformanceStage lookup={session.lyrics} playbackState={session.snapshot.state} />}
        </View>

        <View style={styles.bottomDock}>
          <PlaybackProgress
            disabled={isLoading || isError}
            durationMs={session.snapshot.durationMs}
            positionMs={session.snapshot.positionMs}
            onScrub={session.previewScrub}
            onScrubEnd={(positionMs) => void session.commitScrub(positionMs)}
            onScrubStart={session.beginScrub}
          />
          {isError ? (
            <ErrorControls error={session.error ?? "Could not prepare the instrumental."} onRetry={() => void session.retry()} />
          ) : session.snapshot.state === "ready" ? null : (
            <TransportControls
              state={session.snapshot.state}
              onPause={() => void session.pause()}
              onPlay={() => void session.play()}
              onRestart={() => void session.restart()}
              onSeekBackward={() => void session.seekBy(-SEEK_STEP_MS)}
              onSeekForward={() => void session.seekBy(SEEK_STEP_MS)}
            />
          )}
        </View>
      </View>
    </SafeAreaView>
  );
}

function LoadingStage() {
  return <View style={styles.loadingStage}><Text style={styles.loadingTitle}>Preparing instrumental...</Text><Text style={styles.loadingBody}>Lyrics will follow the actual playback position.</Text></View>;
}

function ErrorControls({ error, onRetry }: { error: string; onRetry: () => void }) {
  return <View style={styles.errorControls}><Text style={styles.errorText}>{error}</Text><Pressable accessibilityRole="button" style={styles.retryButton} onPress={onRetry}><Text style={styles.retryLabel}>Retry</Text></Pressable></View>;
}

function UnavailableSongScreen({ message }: { message: string }) {
  const router = useRouter();
  return <SafeAreaView style={styles.unavailableScreen}><StatusBar style="light" /><Text style={styles.unavailableTitle}>Song unavailable</Text><Text style={styles.unavailableBody}>{message}</Text><Pressable accessibilityRole="button" style={styles.retryButton} onPress={() => router.replace("/")}><Text style={styles.retryLabel}>Back to library</Text></Pressable></SafeAreaView>;
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: "#0a0910", flex: 1, overflow: "hidden" },
  screen: { flex: 1 },
  header: { alignItems: "flex-start", flexDirection: "row", justifyContent: "space-between", paddingHorizontal: 24, paddingTop: 12 },
  headerButton: { alignItems: "center", backgroundColor: "rgba(255,255,255,0.15)", borderRadius: 18, height: 36, justifyContent: "center", width: 36 },
  headerButtonLabel: { color: "#ffffff", fontSize: 10, fontWeight: "800" },
  trackInfo: { alignItems: "flex-end", flexShrink: 1, maxWidth: "76%" },
  trackTitle: { color: "#ffffff", fontSize: 18, fontWeight: "800", textAlign: "right" },
  trackArtist: { color: "#ffffff", fontSize: 13, fontWeight: "600", marginTop: 2, opacity: 0.78, textAlign: "right" },
  nowPlaying: { color: "#ffffff", fontSize: 10, fontWeight: "800", letterSpacing: 2.4, marginTop: 8, opacity: 0.9, textTransform: "uppercase" },
  lyricRegion: { flex: 1, minHeight: 0, justifyContent: "center" },
  bottomDock: { gap: 18, justifyContent: "center", minHeight: 164, paddingBottom: 12, paddingTop: 14 },
  loadingStage: { alignItems: "center", flex: 1, justifyContent: "center", paddingHorizontal: 24 },
  loadingTitle: { color: "#ffffff", fontSize: 20, fontWeight: "800" },
  loadingBody: { color: "#ffffff", fontSize: 16, marginTop: 8, opacity: 0.75, textAlign: "center" },
  errorControls: { alignItems: "center", gap: 16, paddingHorizontal: 24 },
  errorText: { color: "#ffffff", fontSize: 14, lineHeight: 20, textAlign: "center" },
  retryButton: { alignItems: "center", backgroundColor: "#ffffff", borderRadius: 24, justifyContent: "center", marginTop: 20, minHeight: 48, paddingHorizontal: 24 },
  retryLabel: { color: "#24112b", fontWeight: "800" },
  unavailableScreen: { alignItems: "center", backgroundColor: "#09070f", flex: 1, justifyContent: "center", paddingHorizontal: 32 },
  unavailableTitle: { color: "#ffffff", fontSize: 24, fontWeight: "800", textAlign: "center" },
  unavailableBody: { color: "#ffffff", fontSize: 16, lineHeight: 24, marginTop: 12, opacity: 0.75, textAlign: "center" },
});
