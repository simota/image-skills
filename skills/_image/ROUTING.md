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
| `image-direction` | What the picture must say, and what it should look like saying it | A brief |
| `image-prompt` | The request the generator actually receives | A prompt record |
| `image-generate` | Running it, what it cost, and which candidate survives | Images and recipes |
| `image-refine` | Changing an image that already exists | Images and recipes |
| `image-review` | Whether the result is usable, and what is wrong with it | Nothing. Report-only |
| `image-deliver` | Getting the chosen file into the project in the form it needs | Files and their placement |

**None of these decide what the product is.** A picture making a claim about a
real person, product, or organisation is the human's (`_image/VALUES.md` §6).

**Who decides a value.** Three skills produce pixel dimensions, so one rule
settles it: *the skill that decides a value owns it until it is named*, and
**`image-deliver` owns any size that exists because of where the file goes**. A
size chosen to give the model room to work is `image-prompt`'s; the same number
chosen because a container is that wide is `image-deliver`'s.

## Disambiguation

Where two skills are both plausible, `not:` in the registry says where the work
goes. These rows say *how to tell which case you are in*.

| Both plausible | Decided by |
|---|---|
| direction vs prompt | Is what the picture should be settled? Unsettled → direction. Settled, needs wording → prompt |
| prompt vs generate | Is the question about the words or about the run? Words → prompt. How many, what it costs, which one → generate |
| generate vs refine | Does an image exist that is worth starting from? No → generate. Yes → refine |
| refine vs review | **review judges, refine changes.** A run that both judged and fixed cannot say which it did first |
| review vs direction | Does a picture exist? Exists → review. Being decided → direction. A verdict of `usable, off-brief` is review handing it back to direction |
| refine vs deliver | Is the problem in the picture or in the file? Picture → refine. Format, size, placement → deliver |
| anything vs review | review never produces the replacement. It says what is wrong and hands the fix to the owner |

## Chains

The chains that recur are in `registry/routes.yaml`, with their control
structure rather than as prose: which stages, in what order, and what has to
hold before the next one starts.

A chain of names expresses linear work only. Where a stage repeats until a
condition holds — `refine-to-brief` is the one that does — the entry carries the
stopping condition, the judge, and a hard cycle limit. **The judge is never the
engine that produced the image.** Without those three, "until it looks right"
has no stopping rule, and every cycle is paid for.

## Rules for running a chain

- **Settle the brief before the first stage**, including `standard` and
  `budget`. Every stage receives it whole and it does not change mid-run
  (`_image/SIZING.md`)
- **A stage's output is a handoff** (`_image/HANDOFF.md`), and the next stage
  runs the receiver checks before starting — including that every image named
  carries a recipe
- **Never run a deciding skill on work classified as report-only.** "Take a look
  at this" does not authorise a regeneration, and nor does finding something wrong
- **A chain wanting a seventh stage is mis-scoped.** Split the request instead
- Stages run in order. Two skills changing the same image concurrently produces
  two images, not a better one
