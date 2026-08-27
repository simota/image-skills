<!-- image:deferred -->
Purpose: the brief this skill produces, field by field, with what an empty field means.
Read when: writing a brief, or receiving one and checking it is complete.
Source: none — nothing outside this page can move what it states.
Verified: 2026-08-23 — the field list is quoted from `_image/SIZING.md`; nothing
re-runs it automatically, so a change there has to be copied here by hand.

# The direction brief

The brief is the whole output of a `T1` or `T2` direction run. Execution
downstream reads this and nothing else, so a field left implicit is a field
decided by whoever hits it first.

## The fields

```yaml
goal: "<one sentence describing the picture once it exists>"
delivers: "<a single artifact>"
axes: [...]
excludes: [...]
baseline: "<what exists now, opened and described>"
standard: "<what the result is judged against>"
budget: "<paid generations this is worth>"
open_questions: []

# direction adds these three; the four stages downstream read them
subject: "<noun phrase · action · setting · framing · light · negative space>"
crops: ["<composed for>", "<must also survive>"]
references:
  - { source: "<path or description>", took: "...", left: "..." }
```

## What an empty field means

| Field | Empty means |
|---|---|
| `goal` | Nobody has said what the picture is for. Not executable |
| `axes` | Judgement will be "does it look good", which is one oracle and always satisfiable |
| `excludes` | Nothing downstream can check itself against. Not executable |
| `baseline` | The current images were not opened. The whole brief is `asserted` |
| `standard` | Every candidate is arguable and the loop has no exit |
| `budget` | Generation has no stopping point |
| `subject` | The generator invents one |
| `crops` | The picture is composed for one container and clipped by the others |
| `references` | Fine. Most briefs have none, and a brief with none is not worse |

## Worked example

```yaml
goal: "the docs landing page has a header image that says 'this is a tool for
       working, not a toy' without showing a product screenshot"
delivers: "one landing-page header image"
axes:
  - "reads as a workspace, not a stock office"
  - "upper third stays empty enough for a two-line headline at 48px"
  - "sits beside the existing muted, low-chroma screenshots without shouting"
  - "no visible text of its own"
excludes: ["the colour tokens", "the page layout", "any second image"]
baseline: "six existing screenshots, opened: desaturated, cool grey, hard edges,
           no people, all UI"
standard: "the six existing screenshots"
budget: "4 generations"
subject: "a worn wooden desk at an angle · nothing happening · a small room at
          dusk · three-quarter view from standing height · one warm lamp from
          the right · upper third empty"
crops: ["16:9, composed for", "1:1 centre crop must still hold the lamp"]
references: []
open_questions: []
```

## Checking one you received

1. Is every field present? A pointer to a brief is not a brief
2. Does `baseline` describe files, or recall them? A recalled baseline makes
   every claim below it `asserted`
3. Can each axis be falsified? Read it back and ask what would disprove it
4. Is `excludes` non-empty?
5. Does `standard` name something that exists and can be opened?
6. Is `open_questions` empty? Execution does not start otherwise
