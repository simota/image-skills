<!-- image:guidance -->
# How hard a change to make

Every rung changes more of the picture than the one above it and is more likely
to lose something already approved. **Take the lowest rung that can plausibly
work**, and move up only after it has failed.

## The ladder

| Rung | What it is | What it risks |
|---|---|---|
| 1 · Crop or scale | Reframe what already exists, or resample it | Resolution. Nothing else. Not really an edit |
| 2 · Region edit | Change one named area, everything else declared invariant | Local blending, edge seams |
| 3 · Extend | Outpaint the canvas outward | The new area matches the old one badly; lighting continuity |
| 4 · Re-prompt with invariants | Generate again from a modified request, invariants restated | Everything. It is a new picture, and it will not match the approved one |
| 5 · Back to the prompt or brief | The fault is global | The work so far, deliberately |

## The rung the fault picks

- **Composition slightly off, content right** → rung 1. Astonishingly often
  enough, and it costs nothing
- **One object wrong, present, or missing** → rung 2
- **The picture is right but the frame is too tight** → rung 3
- **The medium, the palette, the mood, or the subject is wrong** → rung 5. Not
  rung 4: a re-roll on a global fault is gambling, and rung 5 is the same cost
  with a reason attached
- **Two rung-2 attempts failed the same way** → the fault is not local. Rung 5

## Rung 4 is not a fix

A re-prompt returns a *different picture*. The generator has no seed, so
"regenerate with the hand fixed" means "generate again and hope". Everything
approved about the previous candidate is back in play, and the new candidate
needs reviewing from scratch.

That is sometimes correct — but it is a new generation, recorded as one, marked
`IRREPRODUCIBLE`, and reviewed as one. Calling it a fix is what makes it
dangerous: an approval quietly carries over to an image nobody approved.

## Upscaling

Upscaling is rung 1, and it has one honest use: an image that is right and
smaller than the surface needs. It is not a repair. Every defect scales with
everything else, and a soft region becomes a large soft region.

If a picture needs to be bigger and it is not good enough, the order is fix,
then scale — never the reverse.

## Handing off

Some faults belong to nothing on this ladder. A logo that must be exact, text
that must be typographically correct, a mark that has to be reproduced — these
are composite operations, not generative ones, and the honest move is to say
so and hand it to whoever owns that. Iterating a generator toward a precise
logo is a known way to spend a whole budget.
