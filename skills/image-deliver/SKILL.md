---
name: image-deliver
description: "Getting a picture into the project: file format, srcset, compression budget, colour profile, file naming, and where the file lands. Use once the image is chosen."
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---
<!-- image:contract -->

## Owns

The distance between a chosen picture and a file the project can use — format,
the sizes the surface needs, compression, colour, name, placement, and the text
that stands in for it when it does not load. It changes files, never pictures.

Phases: `TARGET → RESIZE → ENCODE → NAME → PLACE → DESCRIBE`.

## Before starting

- **Read what the project already does.** Existing images name the convention:
  directory, naming, format, and how they are referenced. Match it
- **Get the picture out of the generator's directory first.** A project asset
  living only in the generator's own output folder is one cache clear from gone
- **Know the surface's real dimensions.** A number chosen because the container
  is that wide is this stage's; a number chosen to give the model room was the
  request's, and the two are rarely the same
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
| Choosing a format and a compression level | [format-choice](playbooks/format-choice.md) — decided by what is in the picture, not by habit |
| Naming files and variants | [naming](playbooks/naming.md) — a name that survives a second version and a second size |
| Emitting the set of sizes a surface needs | [export-targets](reference/export-targets.md) — the scale rungs, and what each one is derived from |
| Removing what should not ship with the file | [strip](strip.py) — Exif, XMP, generation parameters and comments go; the profile, the alpha and any content credential stay |
| Colour looks wrong once it is in the page | [colour-and-metadata](reference/colour-and-metadata.md) — profile, stripping, and what must not be stripped |
| Writing the text that replaces the image | [alt-text](reference/alt-text.md) — what it is for decides what it says |
| Measuring what was emitted, and checking the recipes travelled | [imgfacts](imgfacts.py) on every file, [recipe](recipe.py) `check --dir` over the directory |
| The chosen picture is smaller than the surface needs | Do not upscale it here. Hand it back — a resample is a change to the picture |
| A claim here would be expensive to get wrong | [refute](refute.py) — put it to the engines that did not make it, asked to break it rather than to agree. Unrefuted is n engines finding nothing, never proof |
| No convention exists in the project | Emit one format and one naming rule, write both down, and say it is now the precedent |
<!-- deliver:values -->
- Ties break by `_image/VALUES.md`, read top to bottom: looking over assuming ·
  the brief over the best picture · one image well over four nearly · the
  cheapest run that answers the question · the existing set over the better
  picture · the human decides what, the agent decides how. Against all of them:
  **a harness that is correct and avoided has failed** — when the ceremony costs
  more than the decision, say so rather than performing it
<!-- /deliver:values -->

## Always / Never

- Always: open every file you wrote and read its dimensions, format and byte
  size off it. An export pipeline that reports its own intent is reporting a wish
- Always: keep the source at full size in the repository, and derive the rest
- Always: state the compression budget and what each file actually came in at
- Always: get permission first before replacing an image already referenced,
  before deleting an original, and before adding a format the project's build
  does not already handle
- Never: overwrite an existing asset — write a sibling version and let the human
  retire the old one
- Never: strip colour metadata without checking what the surface assumes
- Never: ship a picture whose recipe did not travel with it. The file is the
  artifact and it is `IRREPRODUCIBLE`; the recipe is the only way back
- Never: leave alt text to whoever writes the markup

## Verify with

Every emitted file is opened and its dimensions, format and byte size read off
it (evidence: `measured`), and every reference to it in the project is followed
to make sure it resolves.

- **Sizes are recomputed, not restated**: each derived size follows from the
  source and a stated rung, and both numbers appear
- **Budget overruns are reported as themselves**, not absorbed by quietly
  raising the budget
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

Every file is opened and measured, the naming follows the project's convention,
the source is kept, each reference resolves, the recipe travels with the asset,
and every image has alt text or a stated reason it needs none.
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
- **Not bigger than it is.** The requested scope is the deliverable; thought
  goes deeper into the one thing asked, never wider. **A real problem is the
  exception** — something that would break, is unsafe, or rests on a false
  premise is explained in full (`_image/REPORT.md`)
<!-- /deliver:surface -->
