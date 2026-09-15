# Mobile App Instructions

These instructions apply to the React Native + Expo mobile application.

Also follow the repository root `AGENTS.md`.

---

## Stack

Use:

- React Native,
- Expo,
- TypeScript.

Android is the primary MVP platform.

Expo development builds and native modules are explicitly allowed.

Do not constrain the architecture to Expo Go compatibility.

If low-level audio requirements cannot be met cleanly through existing React Native/Expo APIs, a native Android module is acceptable.

Do not migrate the entire application to native Android merely because one subsystem needs Kotlin/Java/C++.

---

## Primary Responsibilities of Mobile

The mobile application owns:

- karaoke UI,
- song selection for prepared local songs,
- instrumental playback,
- master song timeline,
- synchronized lyric display,
- microphone capture,
- live audio chunk delivery,
- complete vocal recording,
- audio-route handling,
- live pitch visualization,
- provisional live scoring,
- speaker/headphone mode behavior,
- latency handling,
- results display,
- local performance history.

Heavy offline song preparation does NOT belong in the mobile app.

Demucs (separating vocals from instruments) must not run in the normal karaoke session.

---

## Real-Time Audio Architecture

Treat real-time audio as a performance-critical subsystem.

Microphone audio must be:

1. captured continuously,
2. processed as timestamped chunks (small slices of audio),
3. sent to live analysis,
4. simultaneously preserved as a full performance recording.

Do not wait until the end of the song to obtain the only microphone data.

Do not make the live scoring path dependent on uploading the full recording.

---

## Master Timeline

There must be one authoritative song timeline.

The master timeline must drive:

- instrumental position,
- lyric highlighting,
- expected reference melody lookup,
- microphone timestamps,
- live scoring,
- timing analysis.

Do NOT implement karaoke synchronization using independent `setTimeout`/`setInterval` chains.

Do NOT use JavaScript wall-clock timers as the sole source of audio truth.

Prefer timing derived as close as practical to actual playback/audio hardware position.

Avoid clock drift (two timelines slowly becoming unsynchronized).

---

## Latency

Latency means audio delay.

The architecture must account for:

- output latency — delay before playback reaches the listener,
- input latency — delay before microphone audio reaches analysis.

Audio routes may include:

- phone speaker,
- wired headphones,
- Bluetooth headphones/earbuds.

Different routes may have different latency characteristics.

Do not hard-code one universal latency constant and assume it is correct everywhere.

The architecture should permit:

- native/platform timestamps,
- route-specific latency profiles,
- calibration,
- confidence-aware timing,
- post-song synchronization sanity checks.

Timing scores must be calculated after relevant latency correction.

Never penalize the singer for known system delay.

---

## Headphone and Speaker Modes

Both modes are MVP requirements.

### Headphone mode

Assume the microphone primarily contains:

- singer,
- environmental noise.

Do not run speaker-echo cancellation unnecessarily.

### Speaker mode

Assume the microphone contains:

- singer,
- instrumental playback,
- environmental noise.

Use AEC / acoustic echo cancellation (removing the phone's own speaker audio from the microphone) where practical.

AEC may be imperfect.

Speaker mode must preserve signal/confidence information so downstream scoring can become less aggressive when cleanup quality is poor.

Do not pretend speaker-mode audio is as clean as headphone audio.

---

## Preprocessing

Keep preprocessing conservative.

Allowed/expected:

- mono conversion where appropriate,
- basic route handling,
- AEC for speaker mode,
- light filtering,
- light noise handling,
- level handling,
- clipping detection,
- noise-floor estimation,
- voice/silence detection,
- resampling where an analysis engine requires it.

Avoid:

- aggressive denoising,
- aggressive dereverberation,
- live Demucs,
- pitch correction,
- auto-tune,
- processing that changes the actual pitch being graded,
- unnecessary multi-stage "studio cleanup."

The app should tolerate reasonable environments.

It is not required to rescue catastrophically bad recording conditions.

Preserve the original/full vocal recording where practical.

---

## Countdown Calibration

The pre-song countdown should be usable as a noise-floor measurement window.

Noise floor means the normal background sound level before the singer begins.

During the countdown:

- sample environmental audio,
- estimate baseline noise,
- establish useful signal-quality information.

Do not add a separate intrusive calibration screen unless later evidence shows it is necessary.

---

## Pitch Detection

Pitch means how high or low a sung note is.

Keep the live pitch detector behind an abstraction/interface.

The rest of the app should not depend directly on one implementation.

Current candidate engines include:

- pYIN (probabilistic algorithm for tracking sung pitch),
- CREPE (neural-network model for tracking sung pitch).

The pitch detector should conceptually produce data such as:

- timestamp,
- frequency/F0,
- note or normalized pitch representation,
- confidence,
- voiced/unvoiced state.

F0 / fundamental frequency means the main frequency that determines the sung note.

Do not permanently couple UI/scoring to CREPE-specific or pYIN-specific output shapes.

---

## CREPE / On-Device Models

Do not assume a CREPE model is fast enough for live use merely because it works on desktop.

Benchmark on representative Android hardware.

Important metrics include:

- inference duration,
- real-time factor,
- CPU use,
- memory use,
- thermal behavior,
- dropped audio chunks,
- UI responsiveness,
- end-to-end feedback latency.

Smaller CREPE variants may be used live while a larger model is used post-song if measurements justify it.

Do not add multiple model variants without a reason.

---

## Live Pitch UI

Raw pitch readings can be noisy.

The visible pitch indicator may use smoothing (reducing tiny rapid fluctuations) for a stable experience.

Do not destroy or overwrite raw measurements merely to make the UI smoother.

Separate:

- raw analysis data,
- scoring representation,
- visualized representation.

The UI should not jump wildly because of one uncertain frame.

---

## Live Lyrics

Live lyric checking is required.

Do not implement lyrics as only predetermined highlighting.

The live system should attempt to determine whether expected words were actually sung.

Use ASR / automatic speech recognition (turning voice into words) together with:

- known lyrics,
- expected timing,
- current lyric window.

The live path may classify words as:

- correct,
- missed,
- substituted,
- uncertain.

Do not aggressively mark a word wrong while recognition remains uncertain.

A small recognition delay is acceptable.

Live lyric results are provisional.

---

## Timing

Timing means whether lyrics/phrases/notes are sung at the expected moments.

Timing analysis should emphasize:

- word onset (when a word begins),
- phrase onset (when a lyric phrase begins),
- note onset (when a sung note begins), with lower weight.

Do not expect millisecond-perfect human performance.

Use tolerance curves rather than brittle hard cutoffs.

Track early/late direction where useful for feedback.

---

## Live Score

Overall score weights are fixed unless explicitly changed:

- Pitch: 40%
- Lyrics: 30%
- Timing: 30%.

The live score is provisional.

Smooth the displayed score so it changes naturally.

Do not fake smoothness by hiding large persistent errors.

Do not let one low-confidence audio chunk wildly change the user's score.

---

## Note-Level Pitch Scoring

Do not score pitch solely by averaging every raw audio frame.

Frames should contribute to expected note regions.

For each expected note, the conceptual score is:

- 60% pitch accuracy,
- 30% time in tune,
- 10% stability.

Pitch accuracy means closeness to the target note.

Time in tune means the portion of the note spent sufficiently close to the target.

Stability means how steadily the user held the target note.

Natural vibrato (small controlled pitch wobble) must not automatically count as instability.

Use confidence-aware handling.

Low-confidence detection should not create confident penalties.

---

## Octave Tolerance

Octave means the same musical note at a higher/lower register.

Pitch scoring is octave-tolerant.

Example:

- expected G4,
- user sings G3,

should normally be treated as the same note identity for the current MVP scoring model.

A different note such as F#3 is still a pitch error.

Do not implement key transposition in the MVP.

---

## React Performance

Do not route high-frequency raw audio data through normal React component state unnecessarily.

Avoid causing React renders for every audio sample/chunk.

Prefer:

- dedicated audio/native processing,
- buffers,
- refs,
- worklets/native callbacks,
- throttled UI updates.

Keep visual refresh rate separate from analysis frequency.

A detector may run far more frequently than the screen needs to update.

---

## Native Modules

Native modules are allowed and expected if required.

When introducing native code:

- isolate it behind a TypeScript interface,
- document platform-specific behavior,
- avoid leaking Android implementation details throughout UI code,
- keep fallback/error behavior explicit,
- verify cleanup of native audio resources.

Do not create native code merely to appear performant when a maintained library already solves the requirement.

---

## Audio Lifecycle

Pay special attention to:

- app backgrounding,
- interrupted audio sessions,
- route changes,
- Bluetooth connection/disconnection,
- microphone permissions,
- playback cancellation,
- screen navigation,
- component unmounting,
- recorder cleanup.

Never leave microphones/audio engines running unintentionally.

---

## Error Handling

Surface meaningful states for:

- microphone permission denied,
- unavailable audio input,
- unsupported audio configuration,
- pitch engine failure,
- recording failure,
- poor signal quality,
- analysis unavailable.

Do not fabricate scores as an error fallback.

---

## UI Quality

The MVP must be presentable.

Functional correctness has priority, but "temporary engineering UI forever" is not acceptable.

Maintain:

- consistent typography,
- sensible spacing,
- clear lyric hierarchy,
- smooth feedback,
- readable live scores,
- understandable result states.

Avoid overdecorating before the audio loop works.

Build reusable design primitives early enough that Day 13 polish does not require rewriting every screen.

---

## Verification

For every real-time audio change, test on an actual Android device where practical.

An emulator is not sufficient evidence for:

- microphone timing,
- Bluetooth behavior,
- speaker-mode AEC,
- real-world latency,
- live pitch performance.

When modifying live audio code, test at minimum:

1. headphones,
2. phone speaker,
3. silence,
4. sustained singing,
5. start/stop/restart behavior.

When Bluetooth-related behavior changes, test Bluetooth separately.