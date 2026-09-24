import { useLocalSearchParams } from "expo-router";

import { KaraokeSessionScreen } from "@/features/karaoke";

export default function KaraokeRoute() {
  const { songId } = useLocalSearchParams<{ songId?: string | string[] }>();
  const resolvedSongId = Array.isArray(songId) ? songId[0] : songId;

  return <KaraokeSessionScreen songId={resolvedSongId} />;
}
