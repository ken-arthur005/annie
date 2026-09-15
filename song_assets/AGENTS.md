# Song Assets Instructions

These instructions apply to prepared songs, reference metadata, lyrics timing, melody data, and other song-package assets.

Also follow the repository root `AGENTS.md`.

---

## Purpose

`song-assets/` contains prepared data consumed by the karaoke application.

A prepared song package may include:

* instrumental audio,
* lyrics timing,
* melody/reference pitch data,
* song metadata.

Reference vocal audio used during preparation should generally remain outside the runtime mobile package unless explicitly required.

---

## Treat Reference Data as Scoring-Critical

Song reference data is effectively the scoring answer key.

Do not casually edit:

* note timestamps,
* expected pitches,
* lyric timings,
* phrase boundaries,
* section boundaries,

merely to make a test pass.

If scoring appears wrong, determine whether the defect is in:

* reference data,
* alignment,
* detection,
* scoring logic,

before changing assets.

Never "fix" an algorithm by corrupting the expected reference.

---

## Expected Package Shape

The conceptual runtime package is:

```text
song-id/
├── instrumental.*
├── lyrics.json
├── melody.json
└── metadata.json
```

Exact formats may evolve, but maintain clear separation of concerns.

Do not embed large binary audio directly into JSON.

---

## Instrumental

The instrumental is the accompaniment played while the user sings.

For the MVP:

* use the prepared original-key instrumental,
* do not generate multiple transposed versions,
* do not implement automatic key shifting.

Transposition means moving the whole song higher/lower while preserving the melody.

It is out of scope for the MVP.

---

## Lyrics Data

Lyrics data should support:

* lines/phrases,
* individual words where practical,
* start timestamps,
* end timestamps,
* stable IDs where useful.

All timings must use the same canonical song timeline as melody/reference data.

Do not maintain separate incompatible timing origins.

Prefer seconds or another explicit consistent time unit.

Document the unit in the schema.

---

## Melody Data

Melody data means the expected sung musical pitch over time.

Store both when available:

1. discrete note regions,
2. continuous pitch contour.

Pitch contour means how pitch changes through time.

A discrete note region should contain enough information to identify:

* expected pitch,
* start time,
* end time.

Continuous pitch points should contain enough information to identify:

* timestamp,
* pitch representation,
* confidence where appropriate.

Do not assume raw frequency in Hz is the only useful representation.

Musical pitch representations such as MIDI-like values may also be retained where useful.

---

## Phrase / Section Hierarchy

Reference data should support useful grouping.

Conceptually:

```text
song
└── section
    └── phrase
        └── note
```

A phrase means a short musical/lyric unit.

A section means a larger song part such as a verse or chorus.

This hierarchy allows:

* section-level scores,
* best/weakest section feedback,
* localized debugging.

Do not create unnecessary hierarchy when data does not support it, but preserve meaningful groupings.

---

## Timing Consistency

All assets must align to the same master song timeline.

If:

* lyrics say a word begins at 12.40,
* melody says its expected note begins around 12.40,

those timestamps must refer to the same audio origin.

Do not manually add device latency into song assets.

Device/audio-route latency belongs to runtime synchronization, not static song-reference files.

---

## No Device-Specific Data

Do not store:

* AirPods latency,
* Samsung-specific offsets,
* microphone gain,
* device calibration,

inside song assets.

Song assets describe the song.

Runtime/device profiles describe the playback/recording environment.

Keep them separate.

---

## Schema Changes

Treat schema changes as migrations.

Before changing `lyrics.json`, `melody.json`, or `metadata.json` structure:

1. inspect every consumer,
2. update schema/types,
3. update generators,
4. update validation,
5. update fixtures,
6. update documentation.

Do not silently support multiple ambiguous versions.

Include a schema/data version where appropriate.

---

## Validation

Prepared assets should be machine-validated before use.

Validate:

* required fields,
* timestamps are finite,
* timestamps are ordered,
* start <= end,
* notes/words are within song duration,
* pitch values are valid,
* IDs are unique where required,
* JSON is parseable,
* referenced audio files exist.

Do not rely entirely on runtime mobile code to discover malformed assets.

---

## Human Review

Generated data may require manual review.

Manual corrections are allowed when automated extraction is clearly wrong.

When manually modifying generated reference data:

* keep the change minimal,
* document why when non-obvious,
* do not reshape large sections casually.

The goal is a trustworthy answer key, not perfectly untouched generated output.

---

## Git / Large Files

Be careful with audio-file size.

Do not accidentally commit:

* temporary Demucs stems,
* duplicate intermediate audio,
* model caches,
* rendered debug audio,
* huge experiment outputs.

Only keep runtime assets and deliberately retained reference/test files.

If repository size becomes a problem, stop and choose an explicit large-file strategy rather than silently bloating Git history.

---

## MVP Constraint

The MVP requires one excellent prepared song before it requires a scalable song library.

Optimize first for correctness of the initial song package.

Do not build a generalized content-management system for songs during the MVP.
