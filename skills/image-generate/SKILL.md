---
name: image-generate
description: "Turning a settled prompt into files: run the generation, how many candidates, a batch of candidates, the recipe retained candidates need, and pick the keeper. Use when pixels must exist."
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---
<!-- image:contract -->

## Owns

The paid part. It invokes the generator, decides how many attempts the question
is worth, records what each run was, opens what comes back, and names the one
that survives. Selection removes obvious failures and compares candidates; it
  is not the usability verdict. It does not write the prompt or place the file.

Phases: `BUDGET → INVOKE → CAPTURE → OPEN → SELECT`.

## Before starting

- **Know the budget.** Generation and generative refinement share spend,
  including failed/refused attempts with unknown billing. The brief carries a
  `budget`; a run without one is a run with no end
- **Say what this batch would answer.** A batch launched because the last batch
  disappointed is a batch with no question
- **Check the size is legal before spending anything**, against the generator
  that will run it. One rejects an invalid canvas; the other has no pixel lever
  at all and refuses a shape off its list. A round trip spent on the wrong
  question teaches nothing
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
| Deciding how many candidates to run | [batching](playbooks/batching.md) — one for a settled prompt, a spread only while the direction is still moving |
| Choosing between what came back | [selection](playbooks/selection.md) — against the brief's axes, in a fixed order, before any of them is admired |
| Two generators are installed and neither was named | Ask. They take different size arguments and one writes JPEG — the choice is the user's, and the recipe records which one ran |
| Invoking the pixel-size generator | [codex-imagen](reference/codex-imagen.md) — the two modes, what each takes, and where the file lands |
| Invoking the aspect-ratio generator | [agy-imagen](reference/agy-imagen.md) — the four parameters, the JPEG it writes, and the error it reports over a file that exists |
| Retaining a generated candidate | [recipe](recipe.py) `capture --from <returned-file> --generator <actual-generator>` — bind provenance to this run, not merely the newest cached file |
| Writing down what a run was | [recipe-sidecar](reference/recipe-sidecar.md) — the seven fields, and the form they travel in |
| The generator refused | Report `BLOCKED`; record the attempt/outcome and known or unknown charge. With no file, there is no image recipe |
| The file came back a different size than asked | Expected on the default path — it takes no size argument. Record both numbers and hand the resize to the stage that owns files |
| A claim here would be expensive to get wrong | [refute](refute.py) — put it to the engines that did not make it, asked to break it rather than to agree. Unrefuted is n engines finding nothing, never proof |
| Nothing in the batch is close | Stop. Two failed batches on one prompt is a prompt problem or a brief problem, and another batch will not find out which |
<!-- deliver:values -->
- Ties break by `_image/VALUES.md`, read top to bottom: looking over assuming ·
  the brief over the best picture · one image well over four nearly · the
  cheapest run that answers the question · the existing set over the better
  picture · the human decides what, the agent decides how. Against all of them:
  **a harness that is correct and avoided has failed** — when the ceremony costs
  more than the decision, say so rather than performing it
<!-- /deliver:values -->

## Always / Never

- Always: view pixels before describing or comparing a candidate visually.
  A technical discard may use file facts, but must not masquerade as a visual check
- Always: read the dimensions and the format off the file that came back, not
  off the request — one generator writes JPEG and no flag changes that
- Always: capture the sent request at invocation; persist a recipe for each
  retained candidate. Memory cannot restore it; mark that loss `IRREPRODUCIBLE`
- Always: get permission first before a batch that exceeds the stated budget
- Never: report a candidate as matching the prompt on the strength of the prompt
- Never: leave a file the project will reference sitting only in the generator's
  own output directory
- Never: quietly reword past a refusal
- Never: keep generating because none of them is quite right — say what the next
  run would answer, and if there is no answer there is no run

## Verify with

Open the pixels of every candidate described or compared. Separately read its
dimensions and format with [imgfacts](imgfacts.py) (`measured` mechanical facts,
not a visual inspection). An unopened candidate supports no visual claim.

- **The keeper is named with the axis that decided it**, not with an adjective
- **Spend is reported**: runs made, runs of budget, and what the next one would
  have been for
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
  graded ones: `swept, 0 markers; 6 decisions / 6 graded`. While either pair
  disagrees the status is not `DONE` (`_image/CONTRACT.md`)
<!-- /deliver:report -->

## Done when

Compared candidates were viewed, retained candidates have recipes with measured
on-disk sizes, the keeper is named against an axis, and all attempts/refusals are
accounted for. This completes selection, not a production usability verdict.
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
