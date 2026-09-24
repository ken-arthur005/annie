import { Animated, StyleSheet, Text, View } from "react-native";
import { useEffect, useRef, useState } from "react";

import type { LyricLookup } from "@/features/lyrics";
import type { LyricLine, TimedLyricSegment } from "@/features/songs/types";

const SLOT_DISTANCE = 104;

type LyricStageProps = { lookup: LyricLookup };

type RailItem = {
  line: LyricLine;
  opacity: Animated.Value;
  translateY: Animated.Value;
};

export function LyricStage({ lookup }: LyricStageProps) {
  const railLines = [lookup.rail.topLine, lookup.rail.centerLine, lookup.rail.bottomLine] as const;
  const railSignature = railLines.map((line) => line?.id ?? "empty").join("|");
  const [items, setItems] = useState<RailItem[]>(() => createInitialItems(railLines));
  const itemsRef = useRef(items);
  const displayedRailRef = useRef(railSignature);

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  useEffect(() => {
    if (displayedRailRef.current === railSignature) return;

    displayedRailRef.current = railSignature;
    const duration = lookup.rail.transitionDurationMs ?? 260;
    const targetLines = [lookup.rail.topLine, lookup.rail.centerLine, lookup.rail.bottomLine] as const;
    let transition: Animated.CompositeAnimation | null = null;
    const frame = requestAnimationFrame(() => {
      const existingItems = itemsRef.current;
      const targetIds = new Set(targetLines.flatMap((line) => line ? [line.id] : []));
      const animations: Animated.CompositeAnimation[] = [];
      const nextItems = targetLines.flatMap((line, slot) => {
        if (!line) return [];

        const existing = existingItems.find((item) => item.line.id === line.id);
        const item = existing ?? {
          line,
          opacity: new Animated.Value(0),
          translateY: new Animated.Value((slot + 1) * SLOT_DISTANCE),
        };

        animations.push(
          Animated.timing(item.opacity, { toValue: 1, duration, useNativeDriver: true }),
          Animated.timing(item.translateY, { toValue: slot * SLOT_DISTANCE - SLOT_DISTANCE, duration, useNativeDriver: true }),
        );
        return [item];
      });

      const exitingItems = existingItems.filter((item) => !targetIds.has(item.line.id));
      for (const item of exitingItems) {
        animations.push(
          Animated.timing(item.opacity, { toValue: 0, duration, useNativeDriver: true }),
          Animated.timing(item.translateY, { toValue: -2 * SLOT_DISTANCE, duration, useNativeDriver: true }),
        );
      }

      setItems([...nextItems, ...exitingItems]);
      transition = Animated.parallel(animations);
      transition.start(({ finished }) => {
        if (finished) setItems((currentItems) => currentItems.filter((item) => targetIds.has(item.line.id)));
      });
    });

    return () => {
      cancelAnimationFrame(frame);
      transition?.stop();
    };
  }, [lookup.rail.bottomLine, lookup.rail.centerLine, lookup.rail.topLine, lookup.rail.transitionDurationMs, railSignature]);

  return (
    <View style={styles.root}>
      <View style={styles.viewport}>
        {items.map((item) => (
          <Animated.View key={item.line.id} pointerEvents="none" style={[styles.lineLayer, { opacity: item.opacity, transform: [{ translateY: item.translateY }] }]}>
            <LineText line={item.line} activeWord={item.line.id === lookup.activeLine?.id ? lookup.activeWord : null} />
          </Animated.View>
        ))}
      </View>
    </View>
  );
}

function createInitialItems(lines: readonly (LyricLine | null)[]): RailItem[] {
  return lines.flatMap((line, slot) => line ? [{ line, opacity: new Animated.Value(1), translateY: new Animated.Value(slot * SLOT_DISTANCE - SLOT_DISTANCE) }] : []);
}

function LineText({ line, activeWord }: { line: LyricLine; activeWord: TimedLyricSegment | null }) {
  return <Text style={styles.line}>{line.segments.map((segment, index) => <LyricWord key={segment.id} segment={segment} leadingSpace={index > 0} active={segment.id === activeWord?.id} />)}</Text>;
}

function LyricWord({ segment, leadingSpace, active }: { segment: TimedLyricSegment; leadingSpace: boolean; active: boolean }) {
  const [highlight] = useState(() => new Animated.Value(active ? 1 : 0));

  useEffect(() => {
    Animated.timing(highlight, { toValue: active ? 1 : 0, duration: 140, useNativeDriver: false }).start();
  }, [active, highlight]);

  return <Animated.Text style={[styles.word, { color: highlight.interpolate({ inputRange: [0, 1], outputRange: ["#ffffff", "#e8fa57"] }), transform: [{ scale: highlight.interpolate({ inputRange: [0, 1], outputRange: [1, 1.035] }) }] }]}>{`${leadingSpace ? " " : ""}${segment.text}`}</Animated.Text>;
}

const styles = StyleSheet.create({
  root: { flex: 1, justifyContent: "center", paddingHorizontal: 28 },
  viewport: { height: SLOT_DISTANCE * 3, overflow: "hidden" },
  lineLayer: { left: 0, position: "absolute", right: 0, top: SLOT_DISTANCE },
  line: { color: "#ffffff", fontSize: 32, fontWeight: "800", lineHeight: 42, textAlign: "center" },
  word: { fontWeight: "800" },
});
