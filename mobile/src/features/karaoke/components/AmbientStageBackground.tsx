import { LinearGradient } from "expo-linear-gradient";
import { StyleSheet, View } from "react-native";

type AmbientStageBackgroundProps = {
  variant: "catalog" | "player";
};

export function AmbientStageBackground({ variant }: AmbientStageBackgroundProps) {
  const isCatalog = variant === "catalog";

  return (
    <View className="absolute inset-0 overflow-hidden bg-[#0a0910]" pointerEvents="none" style={styles.root}>
      <LinearGradient
        className="absolute -left-20 -top-28 h-56 w-80 rounded-full"
        colors={isCatalog ? ["#ff83cb", "#9a52df", "transparent"] : ["#d690ef", "#6e478d", "transparent"]}
        locations={[0, 0.48, 1]}
        start={{ x: 0.1, y: 0 }}
        end={{ x: 0.9, y: 1 }}
        style={styles.topGlow}
      />
      <LinearGradient
        className="absolute -right-28 top-20 h-72 w-72 rounded-full"
        colors={isCatalog ? ["#4b246d", "#20142c", "transparent"] : ["#bd70e4", "#281936", "transparent"]}
        locations={[0, 0.44, 1]}
        start={{ x: 0.2, y: 0 }}
        end={{ x: 0.8, y: 1 }}
        style={styles.sideGlow}
      />
      <View className="absolute inset-0 bg-[#0a0910]/55" style={styles.overlay} />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { position: "absolute", top: 0, right: 0, bottom: 0, left: 0, overflow: "hidden", backgroundColor: "#0a0910" },
  topGlow: { position: "absolute", left: -70, top: -98, width: 280, height: 196, borderRadius: 140 },
  sideGlow: { position: "absolute", right: -98, top: 70, width: 252, height: 252, borderRadius: 126 },
  overlay: { position: "absolute", top: 0, right: 0, bottom: 0, left: 0, backgroundColor: "rgba(10, 9, 16, 0.55)" },
});
