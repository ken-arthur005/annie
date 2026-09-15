# Karaoke Scoring App — Project Instructions

## Purpose

This repository contains a serious personal karaoke scoring application.

The core product lets a user sing along to a prepared instrumental while synchronized lyrics are displayed. The application analyzes the performance live and again after the song, producing scores for:

- Pitch — how accurately the user sang the expected musical notes.
- Lyrics — whether the user sang the correct words.
- Timing — whether words/phrases were sung at the expected moments.

The MVP is Android-first, built with React Native + Expo + TypeScript, with Python tooling for offline song preparation and audio-analysis experiments.

This is an audio-heavy engineering project. Correctness, synchronization, explainability, and fair scoring matter more than clever abstractions.

---

## Instruction Scope

This root file contains repository-wide rules.

More specific instructions exist inside major directories:

- `mobile/AGENTS.md`
- `audio-lab/AGENTS.md`
- `song-assets/AGENTS.md`

When working inside one of those areas, follow both this file and the nearest applicable nested `AGENTS.md`.

Do not create conflicting interpretations between instruction files.

---

## Source of Truth

The intended hierarchy is:

1. The user's current explicit request.
2. `docs/ARCHITECTURE.md` for agreed product/audio/scoring architecture.
3. Applicable `AGENTS.md` files.
4. Existing tests and established code behavior.
5. Existing implementation details.

If a requested change conflicts with `docs/ARCHITECTURE.md`, do not silently preserve the old architecture and do not silently ignore the document.

Instead:

1. identify the conflict,
2. implement the user's new decision,
3. update the architecture documentation when appropriate.

Never casually change core scoring/audio behavior as an unrelated refactor.

---

## Product Scope — MVP

The current MVP is intentionally constrained.

Build for:

- one prepared song,
- Android first,
- React Native + Expo + TypeScript,
- live karaoke playback,
- synchronized lyrics,
- continuous microphone capture,
- live pitch feedback,
- live lyric checking,
- live timing analysis,
- continuously changing live score,
- full-performance recording,
- more accurate post-song analysis,
- final performance report,
- headphone mode,
- speaker mode.

Do NOT add unrelated product scope unless explicitly requested.

Examples of out-of-scope MVP features:

- authentication,
- user accounts,
- social feeds,
- leaderboards,
- Spotify integration,
- arbitrary user-uploaded songs,
- automatic song discovery,
- automatic key transposition,
- iOS-specific optimization,
- cloud sync,
- deep AI vocal coaching,
- multiplayer,
- public deployment infrastructure.

Ideas may be noted for later, but do not implement them without instruction.

---

## Locked Scoring Decisions

Do not change these values unless explicitly requested.

### Overall performance score

- Pitch: 40%
- Lyrics: 30%
- Timing: 30%

### Single-note pitch score

- Pitch accuracy: 60%
- Time in tune: 30%
- Stability: 10%

Definitions:

- Pitch — how high or low a sung musical note is.
- Time in tune — how much of an expected note was sung sufficiently close to the target pitch.
- Stability — how steadily the user held the expected note.
- Octave — the same note at a higher or lower register.

Pitch scoring is octave-tolerant: singing the same note one or more octaves higher/lower should not automatically be treated as a wrong note.

Do not use raw audio-frame averages as the final pitch score. Aggregate pitch measurements into expected notes, then notes into phrases/sections/song-level results.

---

## Live vs Final Analysis

The application intentionally has two analysis paths.

### Live analysis

Optimize for:

- low latency,
- responsiveness,
- useful provisional feedback.

Live results may be approximate.

### Post-song analysis

Optimize for:

- greater accuracy,
- better alignment,
- more careful scoring.

The final score may differ moderately from the ending live score.

Do not force expensive post-processing into the latency-sensitive live loop merely for architectural uniformity.

---

## Confidence Principle

A fundamental project rule is:

> Bad audio must not automatically be interpreted as bad singing.

Audio/pitch/lyrics/timing analysis should preserve confidence information where possible.

When the system is uncertain because of:

- noise,
- speaker bleed,
- weak pitch detection,
- uncertain speech recognition,
- clipping,
- poor signal quality,

prefer reducing confidence, reducing weight, or marking a result uncertain rather than confidently penalizing the singer.

---

## Cost Constraint

Prefer, in this order:

1. free local/open-source solutions,
2. self-hostable solutions,
3. genuinely useful free tiers,
4. paid services only with explicit approval.

Before adding any dependency, API, model, platform, or service that may cost money:

1. clearly identify the cost,
2. explain why it is needed,
3. wait for explicit approval before making it required.

Do not silently introduce paid APIs.

Existing preferred free/local technologies include:

- React Native,
- Expo,
- Python,
- FastAPI if eventually needed,
- librosa,
- pYIN,
- CREPE,
- Demucs.

---

## Engineering Rules

### Understand before editing

Before changing a subsystem:

1. inspect the relevant existing code,
2. inspect the nearest `AGENTS.md`,
3. inspect applicable tests,
4. inspect `docs/ARCHITECTURE.md` when the change affects product/audio/scoring architecture.

Do not rewrite a subsystem merely because another implementation looks cleaner.

### Keep diffs focused

Prefer the smallest coherent change that solves the requested task.

Do not:

- refactor unrelated modules,
- rename unrelated files,
- change public interfaces without reason,
- introduce new frameworks for convenience,
- add speculative abstractions.

### Dependencies

Before adding a dependency:

- verify that the existing stack cannot reasonably solve the problem,
- prefer actively maintained libraries,
- prefer cross-platform libraries where appropriate,
- consider binary/app-size and runtime-performance costs,
- note licensing/cost implications,
- explain why the dependency exists.

Do not add multiple libraries that solve the same problem without a benchmark or explicit reason.

### No fake implementations

Do not report something as implemented when it is:

- mocked,
- hard-coded,
- placeholder-only,
- not connected to the real pipeline,
- not tested on the intended path.

Mocks are acceptable during isolated development, but label them clearly.

### No silent fallbacks

If an analysis engine fails, do not silently return a plausible-looking score.

Failures should either:

- degrade explicitly,
- lower confidence,
- return unavailable/uncertain,
- or surface an actionable error.

A fake score is worse than no score.

---

## Verification

Do not declare work complete without verification appropriate to the change.

For TypeScript/mobile changes, run the project's available:

- typecheck,
- lint,
- relevant tests.

For Python changes, run:

- relevant tests,
- static/type checks if configured,
- the smallest meaningful audio fixture where appropriate.

For scoring changes, test at least:

- a clearly good input,
- a deliberately bad input,
- a boundary/uncertain input.

Never invent command names.

Inspect `package.json`, Python project files, scripts, or existing documentation and use the actual commands defined by the repository.

If the repository does not yet have appropriate verification commands, say so rather than pretending they ran.

---

## Testing Philosophy

The scoring system must be validated for:

- accuracy — clearly better performances should generally score better,
- repeatability — identical recordings should produce approximately identical results,
- robustness — reasonable recording-condition changes should not destroy scoring,
- live/final consistency — live and final results should broadly agree.

Whenever changing scoring logic, consider regression fixtures.

Do not tune scoring solely against one successful recording.

---

## Architecture Discipline

Keep the following conceptual areas separable:

- song preparation,
- audio playback,
- microphone capture,
- preprocessing,
- pitch detection,
- lyric recognition,
- timing/alignment,
- scoring,
- final feedback,
- persistence/history.

Do not create one giant "audio service" that owns unrelated responsibilities.

Prefer explicit data structures and small interfaces between stages.

---

## User-Facing Explanations

The project owner is learning audio/music engineering while building this application.

Whenever explaining music/audio concepts to the user, include a very short layman's explanation in parentheses, even if the term was explained previously.

Examples:

- pitch (how high or low a note is)
- octave (the same note higher or lower)
- cents (tiny pitch-distance units; 100 cents = one semitone)
- semitone (one small standard step between musical notes)
- vibrato (a small controlled wobble around a note)
- F0 / fundamental frequency (the main frequency that determines the sung note)
- AEC / acoustic echo cancellation (removing the phone's own speaker audio from the microphone)
- latency (audio delay)
- ASR / automatic speech recognition (turning voice into words)
- forced alignment (matching known lyrics to where they occur in audio)

Keep explanations concise. Do not turn every response into a music theory lesson unless asked.

---

## Communication

When proposing a meaningful architectural change:

1. explain the problem,
2. list the practical options,
3. give the tradeoffs,
4. recommend one,
5. do not implement a major architecture change without a clear reason.

When blocked, identify the exact blocker rather than guessing.

Be precise about whether something is:

- implemented,
- partially implemented,
- experimentally validated,
- theoretically planned,
- or still untested.

---

## Git / Repository Hygiene

Do not commit:

- secrets,
- API keys,
- credentials,
- local environment files containing secrets,
- generated model caches,
- large temporary audio outputs,
- build artifacts,
- Python virtual environments,
- device-specific temporary files.

Before introducing large audio/model assets, verify how they should be tracked.

Prefer reproducible generation of derived song-analysis data where practical.

---

## Performance Mindset

This application has a real-time path.

Avoid unnecessary work inside latency-sensitive loops.

Do not:

- perform large allocations for every audio chunk,
- repeatedly parse static song JSON during playback,
- block the UI thread with audio analysis,
- send high-frequency audio data through expensive JS state updates,
- run heavyweight models live without benchmarking.

Measure before optimizing, but do not ignore obvious real-time constraints.

---

## Final Rule

Do not optimize for making the architecture look impressive.

Optimize for:

1. the singer hearing the song correctly,
2. the microphone data being synchronized correctly,
3. the analysis being fair,
4. the score being explainable,
5. the live experience remaining responsive.