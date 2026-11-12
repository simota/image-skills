<!-- image:guidance -->
# ROUTING — which image skill owns this

A request with an obvious owner calls that skill directly. This is the fallback
and the ordering guide, not a gate.

**Boundaries are defined in `registry/capabilities.yaml`, not here and not in
any skill's description.** Each entry carries what a skill does, what it does
not (`not:`, with where that work goes instead), and the words that select it.
An exclusion written into a description makes every skill added rewrite its
neighbours. The table below is a reading of that file, not a second copy.

## Ownership

| Skill | Owns | Writes? |
|---|---|---|
| `image-generate` | Making a picture and changing one: the brief, the request, the run and its keeper, the edit, the file in the project | Briefs, prompt records, images, recipes, files and their placement |
| `image-review` | Whether the result is usable, and what is wrong with it | Nothing. Report-only |

**None of these decide what the product is.** A picture making a claim about a
real person, product, or organisation is the human's (`_image/VALUES.md` §6).

**Who decides a value.** Three phases of `image-generate` produce pixel
dimensions, so one rule settles it: *the phase that decides a value owns it until
it is named*, and **DELIVER owns any size that exists because of where the file
goes**. A size chosen to give the model room to work is PROMPT's; the same number
chosen because a container is that wide is DELIVER's.

## Disambiguation

Where two skills are both plausible, `not:` in the registry says where the work
goes. These rows say *how to tell which case you are in*.

| Both plausible | Decided by |
|---|---|
| generate vs review | **review judges, generate changes.** A run that both judged and fixed cannot say which it did first |
| which phase of generate | The earliest decision still open: what the picture is → DIRECT; its wording → PROMPT; the run → RUN; a picture worth starting from exists → REFINE; the problem is in the file, not the picture → DELIVER |
| review vs the DIRECT phase | Does a picture exist? Exists → review. Being decided → DIRECT. An off-brief finding, whatever the verdict, is review handing it back |
| anything vs review | review never produces the replacement. It says what is wrong and hands the fix to `image-generate` |

## Chains

The chains that recur are in `registry/routes.yaml`, with their control
structure rather than as prose: which stages, in what order, and what has to
hold before the next one starts.

A chain of two skill names cannot say what a stage did, so each route also
names the phase each stage runs (`make`, `edit`, `judge`, `deliver`). A chain
expresses linear work only. Where a stage repeats until a
condition holds — `refine-to-brief` is the one that does — the entry carries the
stopping condition, the judge, and a hard cycle limit. **The judge is never the
engine that produced the image.** Without those three, "until it looks right"
has no stopping rule, and every cycle is paid for.

## Rules for running a chain

- **Settle the brief before the first stage**, including `standard` and
  `budget`. Every stage receives it whole and it does not change mid-run
  (`_image/SIZING.md`)
- **A stage's output is a handoff** (`_image/HANDOFF.md`), and the next stage
  runs the receiver checks before starting — including that each retained generated candidate
  carries or links its existing recipe
- **Never run a deciding skill on work classified as report-only.** "Take a look
  at this" does not authorise a regeneration, and nor does finding something wrong
- **A chain wanting a seventh stage is mis-scoped.** Split the request instead
- **Candidate selection is not approval.** The one-off fast path stops at a
  candidate; use or publication goes through illustrate. A repaired or restyled
  result is reviewed after the last change, and a set is checked member by member
  and together. Already approved assets can go straight to delivery
- Stages run in order. Two skills changing the same image concurrently produces
  two images, not a better one
