import { Pressable, Text, View } from "react-native";

type SeekControlsProps = {
  disabled: boolean;
  onSeekBackward: () => void;
  onSeekForward: () => void;
};

export function SeekControls({ disabled, onSeekBackward, onSeekForward }: SeekControlsProps) {
  return (
    <View className="flex-row justify-center gap-8">
      <Pressable accessibilityRole="button" disabled={disabled} onPress={onSeekBackward}>
        <Text className="text-sm font-bold text-[#b9aaba]">-5 sec</Text>
      </Pressable>
      <Pressable accessibilityRole="button" disabled={disabled} onPress={onSeekForward}>
        <Text className="text-sm font-bold text-[#b9aaba]">+5 sec</Text>
      </Pressable>
    </View>
  );
}
