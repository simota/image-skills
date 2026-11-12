<!-- image:guidance -->
# Run — turning a settled prompt into files

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

## Decide first

| Situation | How to proceed |
|---|---|
| Deciding how many candidates to run | [batching](batching.md) — one for a settled prompt, a spread only while the direction is still moving |
| Choosing between what came back | [selection](selection.md) — against the brief's axes, in a fixed order, before any of them is admired |
| Two generators are installed and neither was named | Ask. They take different size arguments and one writes JPEG — the choice is the user's, and the recipe records which one ran |
| Invoking the pixel-size generator | [codex-imagen](../reference/codex-imagen.md) — the two modes, what each takes, and where the file lands |
| Invoking the aspect-ratio generator | [agy-imagen](../reference/agy-imagen.md) — the four parameters, the JPEG it writes, and the error it reports over a file that exists |
| Retaining a generated candidate | [recipe](../recipe.py) `capture --from <returned-file> --generator <actual-generator>` — bind provenance to this run, not merely the newest cached file |
| Writing down what a run was | [recipe-sidecar](../reference/recipe-sidecar.md) — the seven fields, and the form they travel in |
| The generator refused | Report `BLOCKED`; record the attempt/outcome and known or unknown charge. With no file, there is no image recipe |
| The file came back a different size than asked | Expected on the default path — it takes no size argument. Record both numbers and hand the resize to the stage that owns files |
| A claim here would be expensive to get wrong | [refute](../refute.py) — put it to the engines that did not make it, asked to break it rather than to agree. Unrefuted is n engines finding nothing, never proof |
| Nothing in the batch is close | Stop. Two failed batches on one prompt is a prompt problem or a brief problem, and another batch will not find out which |

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
dimensions and format with [imgfacts](../imgfacts.py) (`measured` mechanical facts,
not a visual inspection). An unopened candidate supports no visual claim.

- **The keeper is named with the axis that decided it**, not with an adjective
- **Spend is reported**: runs made, runs of budget, and what the next one would
  have been for

## Done when

Compared candidates were viewed, retained candidates have recipes with measured
on-disk sizes, the keeper is named against an axis, and all attempts/refusals are
accounted for. This completes selection, not a production usability verdict.
