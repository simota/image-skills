---
name: image-generate
description: "Turning a settled prompt into files: run the generation, how many candidates, a batch of candidates, the recipe each run leaves behind, and pick the keeper. Use when pixels must exist."
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---
<!-- image:contract -->

## Owns

The paid part. It invokes the generator, decides how many attempts the question
is worth, records what each run was, opens what comes back, and names the one
that survives. It does not write the prompt and does not place the file.

Phases: `BUDGET → INVOKE → CAPTURE → OPEN → SELECT`.

## Before starting

- **Know the budget.** Generation is the only stage in this family that spends
  money per attempt and has no natural stopping point. The brief carries a
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
| Deciding how many candidates to run | [batching](playbooks/batching.md) — one for a settled prompt, a spread only while the direction is still moving |
| Choosing between what came back | [selection](playbooks/selection.md) — against the brief's axes, in a fixed order, before any of them is admired |
| Two generators are installed and neither was named | Ask. They take different size arguments and one writes JPEG — the choice is the user's, and the recipe records which one ran |
| Invoking the pixel-size generator | [codex-imagen](reference/codex-imagen.md) — the two modes, what each takes, and where the file lands |
| Invoking the aspect-ratio generator | [agy-imagen](reference/agy-imagen.md) — the four parameters, the JPEG it writes, and the error it reports over a file that exists |
| Getting a candidate out of the generator's directory | [recipe](recipe.py) `capture --generator <name>` — places the newest generated file and writes its sidecar with the size read off it |
| Writing down what a run was | [recipe-sidecar](reference/recipe-sidecar.md) — the seven fields, and the form they travel in |
| The generator refused | Report it as `BLOCKED` with the refusal. A reworded prompt is a different recipe and is recorded as one |
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

- Always: open every candidate before saying anything about it. A path is not a
  result, and this is the rule the whole set exists to enforce
- Always: read the dimensions and the format off the file that came back, not
  off the request — one generator writes JPEG and no flag changes that
- Always: write the recipe at the moment of the run. A recipe reconstructed
  afterwards is a plausible recipe, and it is marked `IRREPRODUCIBLE` twice over
- Always: get permission first before a batch that exceeds the stated budget
- Never: report a candidate as matching the prompt on the strength of the prompt
- Never: leave a file the project will reference sitting only in the generator's
  own output directory
- Never: quietly reword past a refusal
- Never: keep generating because none of them is quite right — say what the next
  run would answer, and if there is no answer there is no run

## Verify with

Every candidate is opened, and its dimensions and format read off the file by
[imgfacts](imgfacts.py) (evidence: `measured`). A candidate described but not
opened is `asserted` and supports no claim about the batch.

- **The keeper is named with the axis that decided it**, not with an adjective
- **Spend is reported**: runs made, runs of budget, and what the next one would
  have been for
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

Every candidate is opened, every run has a recipe with both sizes recorded, the
keeper is named against a brief axis, spend is stated, and any refusal is
reported as itself.
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
