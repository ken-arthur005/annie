# Karaoke Scoring App — Architecture

## 1. Purpose

This document is the technical source of truth for the karaoke scoring application.

The product is a mobile karaoke application that allows a user to sing along to a prepared instrumental while synchronized lyrics are displayed.

While the user sings, the application analyzes:

* **Pitch** (how high or low the sung notes are)
* **Lyrics** (whether the correct words are being sung)
* **Timing** (whether words, phrases, and notes are sung at the expected moments)

The application provides:

* live pitch feedback,
* live lyric feedback,
* a continuously changing provisional score,
* post-song analysis,
* a final performance score,
* a short performance breakdown.

The product is designed primarily as a fun karaoke application, not a professional vocal-coaching system.

---

# 2. MVP Scope

The first MVP supports:

* Android first
* React Native + Expo + TypeScript
* one prepared song
* instrumental playback
* synchronized lyrics
* continuous microphone capture
* headphone mode
* speaker mode
* live pitch detection
* live lyric checking
* live timing analysis
* live overall score
* full-performance recording
* more accurate post-song analysis
* final performance report
* local attempt history

The MVP does NOT initially include:

* automatic key transposition (moving the whole song higher/lower)
* arbitrary user-uploaded songs
* Spotify/Apple Music integration
* user accounts
* cloud sync
* social features
* leaderboards
* deep AI vocal coaching
* public song library management
* iOS-specific optimization
* advanced pronunciation scoring
* advanced expressive/performance scoring

---

# 3. Technology Direction

## Mobile application

Primary stack:

* React Native
* Expo
* TypeScript

Expo development builds and native modules are allowed.

Expo Go compatibility is NOT a requirement.

React Native owns:

* UI
* navigation
* karaoke experience
* lyrics
* playback orchestration
* recording orchestration
* live feedback
* live scoring
* local history

Native Android/Kotlin/C++ modules may be introduced where low-level audio requirements demand them.

React Native remains the application framework even if some audio-engine components are implemented natively.

---

## Python audio laboratory

Python is used for:

* offline song preparation
* Demucs processing
* pYIN experiments
* CREPE experiments
* reference melody generation
* note segmentation
* pitch benchmarking
* scoring experiments
* post-song analysis experiments

Likely libraries include:

* NumPy
* SciPy
* librosa
* pYIN
* CREPE
* Demucs

These are local/open-source tools and do not require paid APIs.

---

## Backend

A backend is optional.

If eventually required, Python + FastAPI is the preferred direction.

A backend may later handle:

* heavier post-song analysis
* expensive models
* transcription
* forced alignment (matching known lyrics to where they occur in audio)
* optional history sync

The backend must NOT be placed inside the latency-sensitive live karaoke loop unnecessarily.

The application should remain capable of providing its core live experience without waiting on network requests.

---

# 4. Repository Structure

Conceptual structure:

```text
project/
├── AGENTS.md
├── mobile/
│   ├── AGENTS.md
│   └── ...
├── audio-lab/
│   ├── AGENTS.md
│   └── ...
├── song-assets/
│   ├── AGENTS.md
│   └── ...
├── docs/
│   └── ARCHITECTURE.md
└── backend/
    └── ...   # only if/when required
```

---

# 5. High-Level Architecture

The system consists of two major phases:

1. offline song preparation
2. runtime karaoke analysis

```text
=====================================================
               OFFLINE SONG PREPARATION
=====================================================

                  ORIGINAL SONG
                        │
                        ▼
                     DEMUCS
                   /         \
                  ▼           ▼
          REFERENCE VOCAL   INSTRUMENTAL
                  │
                  ▼
         PITCH EXTRACTION
            pYIN / CREPE
                  │
                  ▼
           PITCH CONTOUR
                  │
                  ▼
          NOTE SEGMENTATION
                  │
                  ▼
             melody.json

               TIMED LYRICS
                   │
                   ▼
              lyrics.json

        REVIEWED SONG STRUCTURE
                   │
                   ▼
             structure.json

                   │
                   ▼
          PREPARED SONG PACKAGE


=====================================================
                  KARAOKE SESSION
=====================================================

                PREPARED SONG
                      │
                      ▼
                 3... 2... 1...
                      │
                      ▼
             NOISE-FLOOR SAMPLE
                      │
                      ▼
              START INSTRUMENTAL
                      │
                      ▼
              MASTER SONG CLOCK
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
    INSTRUMENTAL    LYRICS     REFERENCE
      PLAYBACK      DISPLAY      MELODY
                                     
                     USER
                      │
                      ▼
                 MICROPHONE
                      │
                      ▼
                 AUDIO CHUNKS
                      │
             ┌────────┴────────┐
             ▼                 ▼
       LIVE ANALYSIS      FULL RECORDING
             │                 │
      ┌──────┼──────┐          │
      ▼      ▼      ▼          ▼
    PITCH  LYRICS  TIMING   POST ANALYSIS
      │      │      │          │
      └──────┼──────┘          │
             ▼                 │
         LIVE SCORE            │
                               ▼
                         FINAL SCORE
                               │
                               ▼
                       PERFORMANCE REPORT
```

---

# 6. Offline Song Preparation

Song preparation happens before a song is bundled into the app.

It does NOT occur while the user is singing.

## 6.1 Source separation

Demucs is used to separate:

```text
original song
    │
    ▼
  Demucs
   /   \
  ▼     ▼
vocals  instrumental
```

The instrumental becomes the karaoke backing track.

The isolated vocal becomes preparation-only source material.

The isolated vocal is NOT required inside the normal mobile runtime package.

---

# 7. Reference Melody Generation

The reference vocal is analyzed to determine what the original singer is singing musically.

## 7.1 Pitch extraction

Pitch (how high or low a note is) is extracted over time.

Current candidate tools:

* pYIN (probabilistic algorithm for tracking sung pitch)
* CREPE (neural-network model for tracking sung pitch)

Both are free/local.

The resulting continuous pitch data is called the **pitch contour** (how pitch moves over time).

Conceptually:

```text
time      detected pitch

12.00     G4
12.03     G4 + 8 cents
12.06     G4 - 5 cents
12.09     G4 + 2 cents
...
```

Cents are tiny pitch-distance units; 100 cents equals one semitone.

A semitone is one small standard step between musical notes.

---

# 8. Note Segmentation

The continuous pitch contour is converted automatically into discrete musical notes.

Example raw contour:

```text
G4
G4 + 9 cents
G4 - 12 cents
G4 + 5 cents
A4
A4 - 6 cents
A4
```

becomes:

```text
G4: 12.00s → 12.64s
A4: 12.64s → 13.20s
```

This is called **note segmentation** (grouping many tiny pitch readings into meaningful notes).

The segmentation algorithm must:

* smooth small pitch fluctuations
* avoid treating vibrato as many separate notes
* ignore extremely short accidental jumps
* detect meaningful note changes
* preserve timing

Vibrato means a small controlled wobble around a note.

The algorithm should be reusable across songs.

Manual correction is allowed when generated reference data is clearly wrong, but manual note labeling should not be the normal workflow.

---

# 9. Reference Melody Representation

`melody.json` should contain both:

## Discrete notes

Used primarily for scoring.

Conceptually:

```json
{
  "pitch": 67,
  "start": 12.40,
  "end": 13.10
}
```

## Continuous pitch contour

Used for richer analysis and context.

Conceptually:

```json
{
  "time": 12.43,
  "pitch": 67.04,
  "confidence": 0.96
}
```

The continuous contour preserves:

* vibrato
* slides
* bends
* transitions

A slide means smoothly moving from one pitch toward another.

A bend means deliberately changing the pitch of a note.

The user is NOT required to exactly imitate these stylistic details.

The discrete intended notes remain the main scoring reference.

---

# 10. Lyrics Reference

`lyrics.json` contains timed lyrics.

Word-level timing is preferred.

Conceptually:

```json
{
  "line": "I used to rule the world",
  "words": [
    {
      "text": "I",
      "start": 12.20,
      "end": 12.39
    },
    {
      "text": "used",
      "start": 12.39,
      "end": 12.80
    }
  ]
}
```

All lyric timestamps and melody timestamps must use the same canonical song timeline.

---

# 11. Runtime Song Package

A prepared runtime song should conceptually contain:

```text
song-id/
├── instrumental.mp3
├── melody.json
├── lyrics.json
└── metadata.json
```

The reference vocal remains outside the normal runtime package.

---

# 12. Key and Octave Behaviour

## Transposition

Transposition means moving the entire song higher/lower while preserving the melody.

Automatic or manual transposition is NOT part of the MVP.

Songs play in their prepared/original key.

---

## Octave tolerance

An octave means the same musical note at a higher/lower register.

Example:

```text
G3
G4
G5
```

are all versions of G.

Pitch scoring is octave-tolerant.

If the reference expects:

```text
G4
```

and the user sings:

```text
G3
```

the system should generally treat that as the same note identity.

If the user sings:

```text
F#3
```

that remains a pitch error because F# is a different note.

---

# 13. Countdown and Noise Floor

Before singing begins:

```text
3...
2...
1...
```

The countdown is also used to estimate the **noise floor** (normal environmental sound level before singing starts).

This provides information about:

* background noise
* signal quality
* useful voice/noise thresholds

The app should tolerate reasonable recording environments.

It is not responsible for perfectly recovering vocals recorded under catastrophically bad conditions.

If background noise is excessive, the system may warn the user that scoring accuracy could decrease.

---

# 14. Headphone and Speaker Modes

Both are MVP requirements.

## Headphone mode

The microphone should primarily contain:

```text
user voice
+
environmental noise
```

This is the cleaner analysis path.

---

## Speaker mode

The microphone may contain:

```text
user voice
+
instrumental
+
environmental noise
```

Speaker mode therefore uses AEC.

AEC / Acoustic Echo Cancellation means attempting to remove audio played by the device's own speaker from the microphone recording.

Conceptually:

```text
microphone mixture
        +
known instrumental
        │
        ▼
       AEC
        │
        ▼
cleaner vocal signal
```

AEC is not assumed to be perfect.

Remaining contamination should affect confidence rather than automatically being interpreted as user error.

---

# 15. Microphone Capture

The microphone is captured continuously.

The app does NOT simply record the entire song and wait until the end.

The live stream is divided into audio **chunks** (small slices of audio).

```text
[chunk][chunk][chunk][chunk]...
```

Each chunk receives timing information.

Each chunk participates in:

```text
chunk
  │
  ├── live analysis
  │
  └── full performance recording
```

The exact chunk size is not permanently fixed yet.

It will be selected through benchmarking based on:

* detector accuracy
* live latency
* compute cost

---

# 16. Audio Preprocessing

Preprocessing is intentionally conservative.

Pipeline:

```text
MICROPHONE
    │
    ▼
MONO / ROUTE HANDLING
    │
    ▼
SPEAKER MODE?
   / \
 yes  no
  │    │
 AEC   │
  └─┬──┘
    ▼
LIGHT FILTERING
    │
    ▼
LIGHT NOISE HANDLING
    │
    ▼
LEVEL HANDLING
    │
    ▼
CLIPPING DETECTION
    │
    ▼
VOICE / SILENCE DETECTION
    │
    ▼
ANALYSIS
```

Mono means a single audio channel instead of separate left/right channels.

Clipping means audio becoming distorted because the microphone signal is too loud.

Preprocessing should NOT include:

* aggressive denoising
* automatic pitch correction
* auto-tune
* heavy EQ
* live Demucs
* aggressive dereverberation
* processing that changes the pitch being graded

The rule is:

> Clean the signal, but do not improve the singer.

The original/full recording should be preserved where practical.

---

# 17. Master Song Timeline

There must be one authoritative song timeline.

It coordinates:

* instrumental playback
* lyric highlighting
* expected melody lookup
* microphone timestamps
* live scoring
* timing analysis

The application must NOT rely on independent JavaScript timers for musical synchronization.

The actual audio playback position should be used as close as practical to the timing authority.

This avoids **clock drift** (two timelines slowly becoming unsynchronized).

---

# 18. Latency Architecture

Latency means audio delay.

The system must account for:

## Output latency

The delay between asking the device to play audio and the user actually hearing it.

## Input latency

The delay between the user making sound and the analysis system receiving it.

Audio routes may include:

* phone speaker
* wired headphones
* Bluetooth earbuds/headphones

Different routes may have different latency.

The architecture may use:

* native/platform timestamps
* route-specific latency profiles
* calibration
* timing confidence
* post-song synchronization checks

Conceptually:

```text
effective expected time
=
reference time
+ output latency
```

and:

```text
corrected user time
=
captured timestamp
- input latency
```

The timing engine compares corrected values.

One universal hard-coded latency constant must NOT be assumed to work for all devices/routes.

---

# 19. Speaker-Mode Latency Opportunity

Speaker mode provides an additional possibility.

Because the microphone hears the instrumental that the app already knows, cross-correlation may be used.

Cross-correlation means finding where two similar audio patterns line up best.

Conceptually:

```text
known instrumental:
|------audio pattern------|

microphone:
      |------same pattern------|

      <---- delay ---->
```

This may help estimate speaker/playback delay.

---

# 20. Pitch Engine

The pitch engine is responsible for detecting the user's current sung pitch.

The architecture should expose a project-owned interface rather than coupling the entire app to one detector.

Conceptually:

```text
PitchDetector
     │
 ┌───┴────┐
 ▼        ▼
pYIN    CREPE
```

Each implementation should normalize its result into a common structure such as:

```text
timestamp
frequency / F0
pitch representation
confidence
voiced/unvoiced
```

F0 / fundamental frequency means the main frequency that determines what note is being sung.

Voiced means the chunk contains a recognizable pitched vocal sound.

---

# 21. pYIN vs CREPE

No permanent winner has been selected for live mobile use yet.

## pYIN

Advantages:

* lightweight
* proven pitch-tracking approach
* confidence/voicing support
* easier experimentation

## CREPE

Advantages:

* neural-network pitch detection
* potentially stronger under noisy/complex conditions

Tradeoff:

* heavier compute requirements

The plan is to benchmark:

* pYIN
* CREPE tiny
* CREPE small
* CREPE medium
* CREPE large/full where useful

on representative recordings.

Android performance must also be benchmarked before CREPE is selected for live use.

The architecture must make switching detectors possible without rewriting scoring/UI code.

---

# 22. Live Pitch Display

Raw pitch measurements can fluctuate rapidly.

The visible pitch indicator may therefore use **smoothing** (reducing tiny rapid visual changes).

Example:

```text
RAW:
G4
G4 + 9 cents
G4 - 7 cents
G4 + 3 cents

DISPLAY:
G4-ish
```

Raw values must remain available for scoring.

The system should distinguish:

* raw analysis data
* scoring data
* visualized/smoothed data

---

# 23. Note-Level Pitch Scoring

Pitch scoring does NOT operate by simply averaging every raw audio chunk.

Chunks contribute to expected note regions.

Hierarchy:

```text
audio chunks
    │
    ▼
pitch readings
    │
    ▼
expected note
    │
    ▼
note score
    │
    ▼
phrase score
    │
    ▼
section score
    │
    ▼
song pitch score
```

This prevents long notes from dominating the entire score merely because they contain more audio frames.

---

# 24. Single-Note Pitch Score

For every expected note:

```text
Note Score =
60% Pitch Accuracy
+
30% Time In Tune
+
10% Stability
```

## Pitch accuracy

Pitch accuracy means how close the user's typical sung pitch is to the target note.

Pitch distance is measured using cents.

A smooth scoring curve should be used rather than sharp cutoffs.

Conceptually:

```text
0 cents      excellent
20 cents     very good
40 cents     good
60 cents     noticeably off
100 cents    around one semitone wrong
```

Exact values remain tunable through testing.

---

## Time in tune

Time in tune means what percentage of the expected note duration was sung sufficiently close to the target note.

Example:

```text
expected note duration: 1 second
user within tolerance: 0.82 seconds

time in tune ≈ 82%
```

---

## Stability

Stability means how steadily the user maintained the intended note.

Natural vibrato should not automatically be penalized.

Chaotic movement across unrelated notes may reduce stability.

Stability has deliberately low weight because this is a fun karaoke application, not a professional voice examination.

---

# 25. Confidence-Aware Scoring

Confidence must be preserved through analysis.

If the detector has high confidence:

```text
confidence = 0.96
```

the measurement can be trusted strongly.

If confidence is poor:

```text
confidence = 0.31
```

the system should avoid confidently punishing the singer.

Possible treatment:

* lower the measurement's weight
* ignore it
* mark it uncertain

Fundamental principle:

> Bad audio does not automatically equal bad singing.

---

# 26. Live Lyrics Analysis

Live lyric checking is required.

The app does NOT simply highlight lyrics based on predefined timestamps.

The system should attempt to determine whether the expected words were actually sung.

The system already knows:

* expected words
* expected timestamps
* current part of the song

This converts the problem from fully arbitrary speech recognition into constrained lyric checking.

---

# 27. ASR

ASR / Automatic Speech Recognition means turning voice into words.

A likely approach is a Whisper-family/open-source model, but the exact model is not yet permanently locked.

Cost preference:

* free/local first
* self-hostable preferred
* paid transcription APIs only if explicitly approved

Live ASR output is provisional.

---

# 28. Live Lyric Pipeline

Conceptually:

```text
LIVE VOCAL CHUNKS
        +
KNOWN CURRENT LYRIC WINDOW
        │
        ▼
       ASR
        │
        ▼
EXPECTED-vs-DETECTED MATCH
        │
        ▼
correct / missed / substituted / uncertain
```

Recognition is allowed to lag slightly behind the actual sung word.

Do not aggressively mark a word wrong while recognition remains uncertain.

---

# 29. Post-Song Lyrics Analysis

After the song, the full recording can be analyzed more carefully.

Conceptually:

```text
FULL RECORDING
      +
KNOWN FULL LYRICS
      │
      ▼
      ASR
      +
FORCED ALIGNMENT
      │
      ▼
FINAL WORD MAPPING
```

Forced alignment means matching known lyrics to where they occurred in the recorded audio.

Expected word classifications may include:

* correct
* missed
* substituted
* uncertain

Lyrics accuracy and pronunciation must remain conceptually separate.

A different accent should not automatically count as a wrong lyric.

---

# 30. Timing Analysis

Timing determines whether the user sang things at the expected moments.

Main components:

* word onset
* phrase onset
* note onset

An onset means the moment something begins.

Current conceptual timing weighting:

```text
Timing Score =
60% Word Timing
+
30% Phrase Timing
+
10% Note Timing
```

Exact weights may be tuned after testing.

---

# 31. Timing Tolerance

Human singing is not expected to be robotically exact.

Timing should use tolerance curves.

Conceptual starting ranges:

```text
0–100 ms       excellent
100–200 ms     very good
200–350 ms     acceptable
350–500 ms     noticeably early/late
500 ms+        poor
```

These are tunable and not considered scientifically final.

The system should also preserve whether the singer was:

* early
* late

This can produce feedback such as:

> You tended to enter some phrases slightly late.

Timing scoring must happen after system-latency correction.

---

# 32. Overall Scoring

The overall score is currently locked as:

```text
Pitch    40%
Lyrics   30%
Timing   30%
```

Formula:

```text
Overall Score =
0.40 × Pitch
+
0.30 × Lyrics
+
0.30 × Timing
```

Example:

```text
Pitch    84
Lyrics   96
Timing   78

Overall ≈ 86
```

These weights are intentional because the product is a balanced karaoke-performance scorer rather than a pitch-only vocal examination.

---

# 33. Live Score

The live score updates while the user sings.

It uses all currently available provisional information.

The visible score should be smoothed so it changes naturally.

Bad:

```text
88 → 51 → 94 → 57 → 90
```

Better:

```text
84 → 85 → 83 → 86 → 87
```

One uncertain frame should not destroy the visible score.

The live score is explicitly provisional.

---

# 34. Final Score

When singing finishes, the full vocal recording is analyzed again.

Conceptually:

```text
FULL RECORDING
     │
     ├── better pitch analysis
     ├── better lyric recognition
     ├── forced alignment
     ├── better timing analysis
     │
     ▼
FINAL CATEGORY SCORES
     │
     ▼
FINAL OVERALL SCORE
```

The final score may differ slightly from the live ending score.

Example:

```text
Live ending score: 84
Final score:       86
```

A massive unexplained difference between live and final scoring should be treated as a defect or investigation signal.

---

# 35. Performance Report

The final screen should remain fun and understandable.

Core display:

```text
OVERALL SCORE

86 / 100

Pitch      84
Lyrics     96
Timing     78
```

Additional feedback:

* best section
* weakest section
* number of missed lyrics
* timing tendency
* pitch tendency

Example:

```text
Best Section
Final Chorus — 93

Weakest Section
Verse 2 — 72

Lyrics
You missed 2 words.

Timing
You tended to enter some phrases slightly late.

Pitch
Most notes were close to target.
A few sustained notes drifted slightly flat.
```

A sustained note means a note held for a longer time.

Flat means slightly lower than the target pitch.

Sharp means slightly higher than the target pitch.

The MVP does NOT require long LLM-generated vocal-coaching paragraphs.

Simple deterministic/rule-based observations are preferred initially.

---

# 36. Performance History

Attempts should be stored locally.

Conceptually:

```text
Viva La Vida

Attempt 1    74
Attempt 2    81
Attempt 3    86
```

Potential derived values:

* best score
* average score
* attempt count

Cloud sync is not required for MVP.

---

# 37. Validation Strategy

The scoring system must be tested deliberately.

For the same song/section, produce performances such as:

* genuinely good
* intentionally wrong pitch
* intentionally wrong lyrics
* intentionally late
* intentionally early
* partial silence
* quiet singing
* noisy environment
* headphone mode
* speaker mode
* Bluetooth mode

The system should demonstrate:

## Accuracy

Clearly better performances should generally score better.

## Repeatability

The same audio recording should produce approximately the same result repeatedly.

## Robustness

Reasonable changes in recording conditions should not destroy scoring.

## Live/final consistency

Live and final scores should broadly agree.

---

# 38. MVP Test Principle

One especially important validation technique is controlled failure.

Example:

```text
A — genuinely try
B — deliberately sing off-pitch
C — deliberately use wrong lyrics
D — deliberately sing late
E — butcher everything
```

Expected rough relationship:

```text
A > B/C/D > E
```

If deliberately terrible singing receives an excellent score, the scoring system must be investigated before adding more features.

---

# 39. Confidence and Signal Quality

The system should preserve information such as:

* audio quality
* detector confidence
* ASR confidence
* clipping state
* noise level
* AEC quality where available

Conceptual data:

```json
{
  "timestamp": 32.45,
  "voiceDetected": true,
  "noiseLevel": 0.12,
  "clipping": false,
  "signalQuality": 0.91,
  "pitchConfidence": 0.94
}
```

These numbers are conceptual and not a final schema.

Signal quality must influence confidence handling without arbitrarily rewriting the singer's score.

---

# 40. Architectural Separation

Keep the following systems conceptually separate:

```text
Song Preparation
        │
        ▼
Playback / Karaoke Engine
        │
        ▼
Microphone Capture
        │
        ▼
Preprocessing
        │
        ├── Pitch Analysis
        ├── Lyrics Analysis
        └── Timing Analysis
                │
                ▼
             Scoring
                │
                ▼
             Feedback
```

Avoid creating one giant service responsible for all audio and scoring behaviour.

Prefer explicit interfaces between stages.

---

# 41. Data Flow Ownership

The app should own project-specific domain structures.

Do not expose library-specific data structures throughout the entire application.

Examples:

```text
CREPE output
      ↓
convert
      ↓
Project PitchFrame
```

and:

```text
Whisper output
      ↓
convert
      ↓
Project WordDetection
```

This keeps detectors replaceable.

---

# 42. Approximate Domain Models

These are conceptual examples, not final schemas.

## Pitch frame

```ts
type PitchFrame = {
  timestampMs: number;
  frequencyHz: number | null;
  pitchMidi: number | null;
  confidence: number;
  voiced: boolean;
};
```

## Expected note

```ts
type ExpectedNote = {
  id: string;
  startMs: number;
  endMs: number;
  pitchMidi: number;
};
```

## Detected lyric

```ts
type DetectedWord = {
  text: string;
  startMs: number;
  endMs: number;
  confidence: number;
};
```

## Word score

```ts
type WordResult = {
  expectedWord: string;
  detectedWord?: string;
  status: "correct" | "missed" | "substituted" | "uncertain";
  confidence: number;
};
```

## Category results

```ts
type PerformanceResult = {
  overall: number;
  pitch: number;
  lyrics: number;
  timing: number;
};
```

These types may evolve as implementation teaches us more.

---

# 43. Paid Services Policy

The architecture prioritizes free solutions.

Current fundamental technology cost:

```text
React Native      FREE
Expo              FREE for fundamental MVP needs
Python            FREE
FastAPI           FREE
librosa           FREE
pYIN              FREE
CREPE             FREE
Demucs            FREE
local processing  FREE
```

Any future required paid service must be explicitly identified and approved before becoming a project dependency.

---

# 44. Open Technical Decisions

The following decisions are deliberately NOT permanently locked yet.

## Live pitch implementation

Need benchmark:

* pYIN-style solution
* CREPE model variants
* Android performance

## ASR model

Whisper-family/open-source approach is likely, but implementation/model size remains to be tested.

## Exact audio chunk/window size

Must be determined through real testing.

## Exact cents tolerance curve

Needs calibration against real performances.

## Exact timing tolerance curve

Needs calibration against real performances.

## Exact AEC implementation

Needs testing across Android devices and speaker conditions.

## Exact latency calibration technique

The architecture supports calibration, but the final strategy will depend on platform/device testing.

## Backend requirement

No backend should be added until a concrete need justifies it.

---

# 45. MVP Implementation Order

Current two-week direction:

```text
Days 1–3
Song preparation + audio science

Days 4–6
Karaoke playback + microphone capture + synchronization

Days 7–9
Live pitch + timing + provisional scoring

Days 10–11
Lyrics + post-song analysis

Days 12–13
Speaker mode + report + UI polish

Day 14
Validation + tuning
```

Internal milestone targets:

```text
Day 3:
Valid song answer key

Day 6:
Functional karaoke recorder

Day 9:
Live pitch/timing grading

Day 11:
Full performance grading

Day 14:
Presentable validated MVP
```

---

# 46. Definition of MVP Success

The MVP does NOT need scientifically perfect singing evaluation.

It succeeds when:

1. the instrumental plays correctly,
2. lyrics remain synchronized,
3. the microphone continuously captures the singer,
4. live pitch feedback visibly responds to the singer,
5. live lyric checking provides useful provisional results,
6. timing influences scoring,
7. the live overall score responds meaningfully,
8. deliberately better/worse singing produces meaningfully different results,
9. post-song analysis improves reliability,
10. headphone mode works,
11. speaker mode is usable,
12. the final report is understandable and presentable.

The final product should already feel like:

> "Here — sing this song and see what score you get."

rather than:

> "Here is an audio-processing experiment."

---

# 47. Design Principles

When implementation choices become unclear, optimize for these priorities:

1. **Fairness**
   Do not punish the singer for system uncertainty.

2. **Synchronization**
   Audio, lyrics, reference data, and microphone timing must agree.

3. **Responsiveness**
   Live feedback must feel live.

4. **Explainability**
   Scores should have understandable causes.

5. **Replaceability**
   Pitch/ASR engines should be replaceable behind project interfaces.

6. **Simplicity**
   Avoid unnecessary preprocessing and infrastructure.

7. **Free-first**
   Prefer local/open-source technologies.

8. **Fun**
   This is ultimately a karaoke application, not a laboratory instrument.
