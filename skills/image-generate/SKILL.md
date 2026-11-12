---
name: image-generate
description: "Making a picture and placing it in the project: art style, image brief, generation prompt, seed, run the generation, edit a region, upscale, file format, srcset. Use when pixels must exist or change."
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---
<!-- image:contract -->

## Owns

Everything that makes a picture or changes one, from a look nobody has settled
to a file the project references: the brief, the request the generator
receives, the paid run and its keeper, the edit to a picture that exists, and
the export. It never decides whether the result is usable — that verdict
belongs to a reader who did not make it.

Phases: `DIRECT → PROMPT → RUN → REFINE → DELIVER`. **Enter at the earliest
phase whose decision is still open, and stop at the last one asked for.**

## Before starting

- **Name the phase you enter and the one you stop at.** A request for a
  candidate stops at RUN; a request for a file in the project reaches DELIVER
- **Know the budget.** Generation and generative refinement share spend,
  including failed/refused attempts with unknown billing. A run without a
  `budget` is a run with no end
- **Open the phase's page before acting in it.** Each carries its own checks,
  rules and done condition; this page only routes
<!-- deliver:sizing -->
- **Size it before anything else**, first match wins. `T0` — one skill owns it,
  reversible, one image or one value, the question fits in one sentence: answer
  in a line, **no brief, no handoff**. `T1` — a `T0` condition fails: settle the
  brief first. `T2` — two or more skills own parts of it: route it. `T0` drops
  the paperwork, never the evidence. Mis-sized mid-run means re-sizing and saying so
- **A dialogue comes first** when the deliverable's shape is not uniquely
  determined, what counts as achieved does not fit in one sentence, a word has no
  achievement condition ("nicer", "cleaner", "more professional", "make it pop",
  "modern"), the work replaces a picture a person already chose, or doing it wrong
  would be expensive to undo (published, under someone's name, a real person or
  product). Looking at what exists is not executing
- **Settle `standard` in that dialogue** — what the image is judged against.
  Without one, every candidate is arguable and the loop has no exit. `excludes`
  may not be empty and execution waits on an empty `open_questions`
  (`_image/SIZING.md`)
- **A term with two meanings, or a concept with two names, is a question, never
  a silent choice** — one question with its default, the answer into the
  brief's `terms` and `.agents/glossary.md`, and the glossary's names only from
  then on (`_image/SIZING.md` § Terms)
<!-- /deliver:sizing -->
<!-- deliver:recipe -->
- **Retained generated candidates carry a recipe**: `engine`, reported `model`
  (or `unreported`), `prompt` verbatim, `excluded`, `size` requested/on disk,
  `inputs`, `output`. Capture the request at invocation; persist for candidates
  shown, kept or passed onward, not immediate discards. References and text-only
  outputs need no invented generation fields. `IRREPRODUCIBLE` limits exact pixel
  regeneration, not reuse or editing the source (`_image/RECIPE.md`)
<!-- /deliver:recipe -->

## Decide first

| Situation | How to proceed |
|---|---|
| The look is not settled — subject, mood, art style, what a reference gives | [direct](playbooks/direct.md), with [subject-and-frame](playbooks/subject-and-frame.md) and [reference-reading](playbooks/reference-reading.md) |
| The picture is decided and needs wording, exclusions, a canvas or variants | [prompt](playbooks/prompt.md), with [structure](playbooks/structure.md) and [exclusions](playbooks/exclusions.md) |
| A settled prompt must become files | [run](playbooks/run.md), with [batching](playbooks/batching.md) and [selection](playbooks/selection.md) |
| A picture exists and is close but wrong | [refine](playbooks/refine.md), with [locate-then-change](playbooks/locate-then-change.md) and [edit-ladder](playbooks/edit-ladder.md) |
| A reviewed picture must land in the project | [deliver](playbooks/deliver.md), with [format-choice](playbooks/format-choice.md) and [naming](playbooks/naming.md) |
| The picture changed after its last review, and delivery is next | Stop. Selection is not approval: `image-review` reads it first, and an approval never carries over to a regenerated or edited picture |
| Two generators are installed and neither was named | Ask. They take different size arguments and one writes JPEG — the choice is the user's, and the recipe records which one ran |
| A claim here would be expensive to get wrong | [refute](refute.py) — put it to the engines that did not make it, asked to break it rather than to agree. Unrefuted is n engines finding nothing, never proof |
<!-- deliver:values -->
- Ties break by `_image/VALUES.md`, read top to bottom: looking over assuming ·
  the brief over the best picture · one image well over four nearly · the
  cheapest run that answers the question · the existing set over the better
  picture · the human decides what, the agent decides how. Against all of them:
  **a harness that is correct and avoided has failed** — when the ceremony costs
  more than the decision, say so rather than performing it
<!-- /deliver:values -->

## Always / Never

- Always: view pixels before describing, comparing or exporting a picture. File
  facts from [imgfacts](imgfacts.py) are `measured` mechanics, never a visual check
- Always: capture the sent request at invocation and keep a recipe for each
  retained candidate and each generative edit. Memory cannot restore it; mark
  that loss `IRREPRODUCIBLE`
- Always: get permission first before a batch over the stated budget, a real
  person, brand or living artist in the picture, or replacing a file already
  referenced
- Never: report a picture as matching the prompt on the strength of the prompt
- Never: quietly reword past a refusal, or keep generating with no question the
  next run would answer
- Never: deliver a picture that changed since `image-review` last read it

## Verify with

Open the pixels of every picture described, compared or written, and read its
dimensions and format off the file (`measured`), not off the request. The
phase's page says what else it owes.

- **Each phase entered reports its own done condition**, and a phase skipped is
  named with why it was already settled
- **Spend is reported**: runs made, runs of budget, what the next one was for
<!-- deliver:report -->
- **Grade every claim**: `measured` names the measurement method or a located,
  repeatable visual observation, not aesthetic certainty. `inspected` is reasoned
  judgement where measurement cannot settle the decision; say why. Header
  inspection is **not viewing pixels**. `asserted` never supports completion:
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
  graded ones: `swept, 0 markers / 0 in open; 6 decisions / 6 graded`. While
  either pair disagrees the status is not `DONE` (`_image/CONTRACT.md`)
<!-- /deliver:report -->

## Done when

The last phase asked for has met the done condition on its page, every retained
candidate has a recipe with measured on-disk sizes, attempts and refusals are
accounted for, and nothing was delivered unreviewed after its last change.
<!-- deliver:surface -->
- **Say what the moment needs.** Start: one line naming what will be made and what is
  excluded. Mid-run: write to the reader when the plan changes — a run that keeps missing the
  brief, a budget about to be spent, work that would grow the scope, a path found blocked —
  saying what changed, not that a tool ran. Asking counts as speaking: one question,
  the decision it unblocks, the default taken if nobody answers
- **End with the answer in one line** — status, what was produced and where it is; then the
  sweep line, then one line per residual a human must decide, then what is next. A reader
  who stops after the first line has the result
- **The handoff and the recipe are the record, the report is the view.** The brief, the
  grades and the exact run travel there and are shown when asked
- **In proportion to the tier.** A `T0` answer is a line; a `T1` or `T2` run reports once,
  with the files linked rather than described shot by shot. Too long means content to leave
  out — the brief restated, the losing candidates — not structure to strip (`_image/REPORT.md`)
- **Not bigger than it is.** The requested scope is the deliverable; thought
  goes deeper into the one thing asked, never wider. **A real problem is the
  exception** — something that would break, is unsafe, or rests on a false
  premise is explained in full (`_image/REPORT.md`)
<!-- /deliver:surface -->
