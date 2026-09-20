# Training Season Song Package

## Runtime Melody Schema

`runtime/melody.json` is schema version 1 and is the approved pitch-scoring
answer key. All timestamps are seconds on the shared song timeline.

Each note contains its stable ID, start/end times, expected MIDI pitch, note
name, and contiguous `scoringRegions`. Region weights are fixed by mode:

- `stable`: `1.0`
- `transition`: `0.0`
- `uncertain`: `0.5`
- `suppressed`: `0.0`

The runtime schema intentionally excludes pYIN detector confidence, frame
indices, boundary methods, and other preparation internals. Those audit fields
remain in `prep/analysis/pitch.pyin-expression-refined.json`.

`sourcePreparation` in the runtime file records SHA-256 identities for the
approved preparation artifact and its source note/contour data.

## Generation

Regenerate the runtime answer key from the repository root after approving new
preparation data:

```powershell
audio-lab/.venv/Scripts/python.exe audio-lab/generate_runtime_melody.py
```
