---
name: image-refine
description: "Changing an image that already exists: regenerate, edit a region, remove an object, extend the canvas, upscale, and iterate. Use when a result is close but wrong."
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---
<!-- image:contract -->

## Owns

Everything done to a picture after one exists — a targeted edit, a reworked
prompt, an extension, an upscale — and the discipline that keeps an iteration
from drifting into a different picture. It does not decide whether the result
is good enough; that judgement belongs to a reader who did not make the change.

Phases: `LOCATE → CLASSIFY → INVARIANTS → CHANGE → COMPARE`.

## Before starting

- **Locate the defect before touching anything.** "The hand is wrong" is not
  actionable; "the left hand, lower third, six fingers" is. A change aimed at an
  unlocated fault is a new generation wearing the word *fix*
- **Write the invariants down.** Everything that must not move is stated before
  the edit and restated in every iteration, because drift is cumulative and
  invisible one step at a time
- **Keep the original.** The starting image is an `inputs` entry in the new
  recipe, and it stays on disk until the result is accepted
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
  `output` path — the run is written down, not remembered, and `engine` says
  which of the two generators ran. Neither exposes a seed, so a recipe fixes the
  intent and never the pixels: that gap is `IRREPRODUCIBLE`, stated once in the
  handoff and never papered over with a seed nobody has (`_image/RECIPE.md`)
<!-- /deliver:recipe -->

## Decide first

| Situation | How to proceed |
|---|---|
| Turning a complaint into something a model can act on | [locate-then-change](playbooks/locate-then-change.md) |
| Choosing how hard a change to make | [edit-ladder](playbooks/edit-ladder.md) — reprompt, region edit, extend, upscale, hand off; take the lowest rung that can work |
| Picking the edit mode the generator understands | [edit-modes](reference/edit-modes.md) — the taxonomy the backing skill keys off, and what each preserves |
| A transparent cutout is wanted | [cutouts](reference/cutouts.md) — chroma key, then local removal, then check the alpha |
| Checking what moved that should not have | [imgfacts](imgfacts.py) on the before and the after — an edit path changes dimensions or format without saying so |
| The change has failed twice the same way | Stop and hand back. A third attempt at the same rung is how a budget is spent proving nothing |
| A claim here would be expensive to get wrong | [refute](refute.py) — put it to the engines that did not make it, asked to break it rather than to agree. Unrefuted is n engines finding nothing, never proof |
| The fix would change who or what the picture depicts | That is not a refinement. Hand it back |
<!-- deliver:values -->
- Ties break by `_image/VALUES.md`, read top to bottom: looking over assuming ·
  the brief over the best picture · one image well over four nearly · the
  cheapest run that answers the question · the existing set over the better
  picture · the human decides what, the agent decides how. Against all of them:
  **a harness that is correct and avoided has failed** — when the ceremony costs
  more than the decision, say so rather than performing it
<!-- /deliver:values -->

## Always / Never

- Always: one change per iteration. Two changes and a better result teaches
  nothing about either
- Always: open the before and the after and say what moved that should not have
- Always: record each edit as its own recipe, with the source image as `inputs`
- Always: get permission first when the edit would alter a person's appearance,
  a brand mark, or anything already published
- Never: describe an edit as applied without opening the result
- Never: re-run a prompt and call it a fix — a regeneration is a different
  picture, marked `IRREPRODUCIBLE`, and it is not the one that was approved
- Never: drop an invariant because the new result is nicer without it
- Never: upscale to hide a defect. It scales too

## Verify with

Before and after are both opened, and the invariants are checked one by one
against the pair (evidence: `measured` — each invariant is a thing that can be
looked at in a named region). An invariant asserted rather than checked is drift
that has not been noticed yet.

- **Dimensions and format are read off the result**, because an edit path can
  change either without saying so
- **The chain is stated**: how many iterations, what each changed, and what the
  next one would be for
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

The fault was located before the change, the invariants held under inspection,
each step has its own recipe naming its source, and the result was opened and
compared rather than assumed.
<!-- deliver:surface -->
- **Say only what the moment needs.** Start: one line naming what will be made and what is
  excluded. Mid-run: silence, unless the reader must act now — a run that keeps missing the
  brief, a budget about to be spent, work that would grow the scope. Progress is not
  information, and a tool call is already visible. Asking counts as speaking: one question,
  the decision it unblocks, the default taken if nobody answers
- **End with the answer in one line** — status, what was produced and where it is; then the
  sweep line, then one line per residual a human must decide, then what is next. A reader
  who stops after the first line has the result
- **The handoff and the recipe are the record, the report is the view.** The brief, the
  grades and the exact run travel there and are shown when asked
- **Ceiling: `T0` one line · `T1` six · `T2` ten**, plus the files themselves — linked,
  never described shot by shot. Over it means cutting content, not reformatting it: no
  restatement of the brief, no closing summary, no losing candidates (`_image/REPORT.md`)
<!-- /deliver:surface -->
