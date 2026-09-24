import { Text, View } from "react-native";

import type { ExpectedNote } from "@/features/songs/types";

type ExpectedNoteDebugProps = {
  note: ExpectedNote | null;
};

export function ExpectedNoteDebug({ note }: ExpectedNoteDebugProps) {
  return (
    <View className="items-center gap-1 py-2">
      <Text className="text-[10px] font-bold uppercase tracking-[2px] text-[#82748a]">Expected note</Text>
      <Text className="text-sm font-bold text-[#cdbbd1]">
        {note ? `${note.noteName}  MIDI ${note.pitchMidi}` : "No expected note"}
      </Text>
    </View>
  );
}
