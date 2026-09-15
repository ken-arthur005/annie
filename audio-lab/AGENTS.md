# Audio Lab Instructions

These instructions apply to Python-based song preparation, audio experiments, benchmarking, and scoring research.

Also follow the repository root `AGENTS.md`.

---

## Purpose

`audio-lab/` is the controlled experimentation and offline-processing environment.

Its responsibilities include:

- song source separation,
- reference vocal analysis,
- pitch extraction,
- note segmentation,
- model benchmarking,
- song-package generation,
- scoring experiments,
- post-song analysis experiments,
- validation plots/reports.

It is NOT the mobile application.

Do not distort the mobile architecture merely because something is easy to do in Python.

---

## Cost

Prefer local/open-source tools.

Current preferred tools include:

- Python,
- NumPy,
- SciPy where useful,
- librosa,
- pYIN,
- CREPE,
- Demucs.

These should be treated as free/local unless a future dependency introduces an external paid service.

Do not add a paid API without explicit approval.

---

## Reproducibility

Audio experiments must be reproducible.

Prefer scripts/functions over one-off notebook-only logic.

Notebooks are acceptable for exploration/visualization, but important transformations should eventually exist in reusable modules/scripts.

When an experiment influences product behavior:

- record relevant parameters,
- save representative metrics,
- convert successful logic into testable code.

Avoid "I changed random numbers until the graph looked good."

---

## Song Preparation Pipeline

The conceptual offline song-preparation pipeline is:

1. original song,
2. Demucs (separating vocals from instruments),
3. reference vocal,
4. instrumental,
5. pitch extraction,
6. note segmentation,
7. timed lyric preparation,
8. validation,
9. generation of prepared song assets.

Demucs is preparation-time tooling.

Do not design it as part of the live karaoke processing loop.

---

## Reference Vocal

The reference vocal is the isolated sung vocal used to create the scoring answer key.

It is preparation-only data.

The mobile app does not need the full reference vocal during normal karaoke playback unless a future architecture decision explicitly changes this.

Do not score a singer by comparing raw voice timbre directly against the reference singer.

Timbre means the characteristic tone/quality that makes one voice sound different from another.

The user should not be penalized for failing to sound like the original artist.

Extract relevant musical/temporal information instead.

---

## Pitch Representation

Pitch means how high or low a sung note is.

Reference generation should preserve two useful forms:

### Continuous pitch contour

Pitch contour means how pitch moves over time.

Retain:

- timestamp,
- pitch/frequency representation,
- confidence where available,
- voiced/unvoiced state where available.

### Discrete note representation

A note representation groups many pitch measurements into meaningful musical note regions with start/end times.

Both representations have value.

Do not discard the continuous contour merely because note segmentation succeeds.

Do not grade users by requiring exact imitation of every wiggle in the reference contour.

---

## pYIN

pYIN is a probabilistic pitch-tracking algorithm.

It is an approved primary reference/benchmark tool.

When using pYIN, preserve useful outputs such as:

- F0 / fundamental frequency (the main frequency determining the sung note),
- voiced/unvoiced state,
- voiced probability/confidence.

Do not assume every pYIN frame is correct.

Use confidence and temporal context.

---

## CREPE

CREPE is a neural-network pitch tracker.

It is an approved candidate for:

- benchmarking against pYIN,
- post-song analysis,
- potentially live/mobile pitch detection if device benchmarks justify it.

When comparing CREPE variants, measure both:

- accuracy/robustness,
- computational cost.

Do not choose the largest model merely because it is the largest.

---

## Pitch Benchmarking

When comparing pYIN and CREPE, use the same recordings.

Benchmark at least:

- clean solo singing,
- quiet/soft singing,
- louder singing,
- mild environmental noise,
- deliberately unstable pitch,
- speaker-mode-like contaminated audio where useful.

Measure:

- pitch agreement with known/inspected reference,
- octave errors,
- unvoiced/voiced errors,
- confidence behavior,
- processing time,
- real-time factor where relevant.

Real-time factor means processing time divided by audio duration.

Below 1.0 means processing is faster than real time.

Do not choose an engine from one anecdotal recording.

---

## Note Segmentation

Note segmentation means turning a continuous pitch contour into discrete sung notes.

This process should be automatic for normal song preparation.

Do not require manual labeling of every note.

Segmentation should:

- smooth minor measurement noise,
- avoid treating vibrato as many separate notes,
- ignore implausibly short accidental pitch jumps,
- detect meaningful sustained note changes,
- preserve timestamps.

Vibrato means a small controlled wobble around a note.

Slides mean smooth movement from one pitch toward another.

The algorithm may require occasional manual review/correction, but manual correction should be exceptional rather than the entire workflow.

Keep segmentation parameters configurable and testable.

---

## Reference Data Validation

Generated reference data is the scoring answer key.

Treat incorrect reference data as a serious defect.

Before approving a prepared song/section:

- inspect pitch contour,
- inspect note segmentation,
- inspect obvious octave mistakes,
- inspect phrase/section alignment,
- verify timestamps against the instrumental.

Garbage reference data creates garbage scoring regardless of how good the app is.

---

## Lyrics

Lyrics preparation should support word-level timestamps where practical.

Do not assume free-form speech recognition alone defines correct lyrics.

The system already knows the expected words.

Prepare data so later systems can use:

- expected word,
- start time,
- end time,
- phrase/line grouping.

Forced alignment means matching known words to where they occur in audio.

Forced alignment may be used to improve prepared lyric timing.

---

## Scoring Research

Locked overall score:

- Pitch: 40%
- Lyrics: 30%
- Timing: 30%.

Locked single-note pitch structure:

- Pitch accuracy: 60%
- Time in tune: 30%
- Stability: 10%.

Do not silently change these weights while experimenting.

Alternative formulas may be tested separately, but clearly label them as experiments and do not replace production defaults without explicit approval.

---

## Pitch Error

Use musically meaningful pitch-distance units when scoring.

Cents means tiny pitch-distance units where 100 cents equals one semitone.

Semitone means one small standard step between musical notes.

Prefer cents over raw-Hz differences for musical pitch error.

Exact tolerance curves remain tunable through validation.

Avoid brittle cliffs where a tiny additional error causes a huge score drop.

Prefer smooth scoring curves.

---

## Octave Tolerance

Octave means the same note at a higher/lower register.

Current scoring is octave-tolerant.

When evaluating pitch accuracy, normalize octave-equivalent notes appropriately before assigning error.

Do not confuse octave tolerance with key transposition.

Key transposition means shifting the whole song into different notes while preserving the melody.

Key transposition is NOT part of the current MVP.

---

## Confidence

Preserve confidence throughout analysis.

Do not convert uncertain measurements into confident errors.

Low-confidence frames/regions may be:

- down-weighted,
- ignored,
- marked uncertain.

Clearly distinguish:

- user error,
- detector uncertainty,
- poor recording quality.

---

## Test Fixtures

Maintain small, reusable test fixtures.

Prefer a short representative song section for development before repeatedly processing a full multi-minute song.

Include fixtures representing:

- good pitch,
- intentionally wrong pitch,
- correct lyrics,
- wrong lyrics,
- correct timing,
- late/early timing,
- silence,
- noise.

Do not rely only on one full-song manual test.

---

## Generated Outputs

Clearly separate:

- source audio,
- temporary intermediate files,
- generated song-package outputs,
- plots/reports,
- caches/model downloads.

Do not commit huge temporary output directories accidentally.

Generated reference data should include enough version/parameter metadata to reproduce it when practical.

---

## Performance

Do not prematurely optimize offline Python code at the cost of understandability.

However, when evaluating something intended for live/mobile use, explicitly measure runtime.

Desktop speed does not imply mobile viability.

---

## Numerical Stability

Audio algorithms can produce:

- NaN,
- infinity,
- missing F0,
- empty voiced regions,
- invalid timestamps.

Handle these explicitly.

Never allow invalid numeric values to silently enter scoring JSON.

---

## Verification

For changes to reference generation:

1. run the relevant test/fixture,
2. inspect generated outputs,
3. compare expected note/pitch behavior,
4. ensure generated JSON is valid.

For changes to scoring:

1. test a good performance,
2. test a deliberately bad performance,
3. test uncertain/noisy input,
4. verify score ordering makes sense.

For changes to model benchmarking:

- record model version/configuration,
- record input fixture,
- record runtime,
- record quality metrics/observations.

Do not report an experiment as successful solely because it completed without crashing.