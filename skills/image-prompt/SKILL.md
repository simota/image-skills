---
name: image-prompt
description: "Writing the generation prompt: prompt wording, what to exclude, aspect ratio, seed and variants, and the levers that control the result. Use before anything is generated."
allowed-tools: Read, Grep, Glob, Bash, Write
---
<!-- image:contract -->

## Owns

The request the generator actually receives — its structure, its exclusions, the
canvas it asks for, and the set of variants that differ on purpose. It decides
what is said, never whether the picture behind it was worth asking for.

Phases: `CLASSIFY → STRUCTURE → CONSTRAIN → SIZE → VARY → RECORD`.

## Before starting

- **Classify the request first.** The backing skill keys its whole behaviour off
  a use-case slug, and a prompt written without one gets classified anyway —
  by the generator, silently, possibly differently each run
- **Read the brief's exclusions.** They become the `Avoid` line verbatim; a
  prompt that restates the inclusions and drops the exclusions has kept the
  easy half
- **Decide what varies before writing variants.** Four prompts differing in ways
  nobody chose produce four results nobody can compare
<!-- deliver:sizing -->
- **Size it before anything else**, first match wins. `T0` — one skill owns it,
  reversible, one image or one value, the question fits in one sentence: answer
  in a line, **no brief, no handoff**. `T1` — a `T0` condition fails: settle the
  brief first. `T2` — two or more skills own parts of it: route it. `T0` drops
  the paperwork, never the evidence. Mis-sized mid-run means re-sizing and saying so
- **A dialogue comes first** when the deliverable's shape is not uniquely
  determined, what counts as achieved does not fit in one sentence, the request
  carries a word with no achievement condition ("nicer", "cleaner", "premium",
  "more professional"), or the work replaces a picture a person already chose.
  Looking at what exists is not executing
- **Settle `standard` in that dialogue** — what the image is judged against.
  Without one, every candidate is arguable and the loop has no exit. `excludes`
  may not be empty and execution waits on an empty `open_questions`
  (`_image/SIZING.md`)
<!-- /deliver:sizing -->
<!-- deliver:recipe -->
- **Every image an output names carries its recipe.** `engine`, `model`,
  `prompt` verbatim, `excluded`, `size` asked for and size on disk, `inputs`,
  `output` path — the run is written down, not remembered. The generator
  exposes no seed, so a recipe fixes the intent and never the pixels: that gap
  is `IRREPRODUCIBLE`, stated once in the handoff and never papered over with a
  seed nobody has (`_image/RECIPE.md`)
<!-- /deliver:recipe -->

## Decide first

| Situation | How to proceed |
|---|---|
| Writing the prompt body | [structure](playbooks/structure.md) — the order that survives: scene, subject, detail, constraint |
| Deciding what to forbid, and how | [exclusions](playbooks/exclusions.md) — a negative that names a thing beats one that names a feeling |
| Choosing dimensions, or being told a size is invalid | [sizes](reference/sizes.md) — the four constraints a size must satisfy, and the ones that are known good |
| Checking a canvas before a run is paid for | [imgfacts](imgfacts.py) `--check-size 1536x1024` — the four constraints, and the nearest legal size when one fails |
| Working out what the engine will and will not honour | [control-surface](reference/control-surface.md) — the built-in path takes a prompt and little else |
| Producing a set of variants | Change one axis per variant and say which. Four prompts differing on four axes tell you nothing about any of them |
| Exact text must appear in the image | Quote it verbatim, spell hard words letter by letter, and say where it sits. Then plan to check it against the file — rendered text is where these models fail most visibly |
| A claim here would be expensive to get wrong | [refute](refute.py) — put it to the engines that did not make it, asked to break it rather than to agree. Unrefuted is n engines finding nothing, never proof |
| A transparent background is wanted | It is not a prompt setting on the default path. Ask for a flat chroma-key background and hand the removal to the stage that owns files |
<!-- deliver:values -->
- Ties break by `_image/VALUES.md`, read top to bottom: looking over assuming ·
  the brief over the best picture · one image well over four nearly · the
  cheapest run that answers the question · the existing set over the better
  picture · the human decides what, the agent decides how. Against all of them:
  **a harness that is correct and avoided has failed** — when the ceremony costs
  more than the decision, say so rather than performing it
<!-- /deliver:values -->

## Always / Never

- Always: write the prompt as a labelled spec, not a paragraph. The labels are
  what a later reader diffs when the result changes
- Always: keep the sent text verbatim in the record. A paraphrase is a different
  prompt, and the difference is invisible until someone tries to reuse it
- Always: state invariants for an edit — *change only X, keep Y unchanged* — in
  every iteration, not only the first
- Always: get permission first when the prompt names a living artist, a real
  person, or a brand
- Never: ask the built-in path for a pixel size and treat it as agreed. The
  canvas is a request; what comes back is measured off the file
- Never: pile on adjectives to fix a result. One targeted change per iteration,
  or nothing is learned
- Never: leave the exclusions to be inferred from the positive description

## Verify with

The prompt is checked against the brief line by line: every axis present, every
exclusion carried, nothing added that the brief did not ask for (evidence:
`inspected` — the prompt is text, and nothing about it can be measured until a
file comes back).

- **The size is checked before it is sent**, not after a run fails: `measured`
  by [imgfacts](imgfacts.py), which reads those four rules from the registry
- **The record is the recipe's `prompt` field**, verbatim, and the run that uses
  it is `IRREPRODUCIBLE` regardless — the words are all that carries forward
<!-- deliver:report -->
- **Grade every claim**: `measured` (the file was opened and the property read
  off it) supports completion; `inspected` (opened and reasoned over, nothing
  measured) only where nothing can be measured and the entry says why;
  `asserted` never does. **A property taken from the request is `asserted`** —
  the prompt asked for 3:2, it does not report what came back
- **The unit is the decision, not the batch.** Each thing the deliverable
  promised carries a grade or sits in the residuals as `UNSPECIFIED`, and a
  decision in neither is what gets invented at export time by whoever hits it first
- **Report `status`**: `DONE` (every promised decision made, every measurable
  claim measured, zero `UNSPECIFIED`) / `PARTIAL` / `BLOCKED` (say what was tried)
- **Every residual is `BLOCKED` / `OUT-OF-SCOPE` / `DEFERRED` / `UNSPECIFIED`**
  and appears in the handoff's `open`; a run holding `Write` also leaves a
  `#TODO(agent):` marker carrying that class in the document it produced
- **Never omit the sweep** — markers against `open`, promised decisions against
  graded ones: `swept, 0 markers; 6 decisions / 6 graded`. While either pair
  disagrees the status is not `DONE` (`_image/CONTRACT.md`)
<!-- /deliver:report -->

## Done when

The use case is named, the spec is labelled, the exclusions are verbatim from
the brief, the size satisfies every stated constraint, each variant names its
one axis, and the exact text sent is written down.
