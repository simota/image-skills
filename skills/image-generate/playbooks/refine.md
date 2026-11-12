<!-- image:guidance -->
# Refine — changing a picture that exists

## Owns

Everything done to a picture after one exists — a targeted edit, a reworked
prompt, an extension, an upscale — and the discipline that keeps an iteration
from drifting into a different picture. It does not decide whether the result
is good enough; that judgement belongs to a reader who did not make the change.

Phases: `LOCATE → CLASSIFY → INVARIANTS → CHANGE → COMPARE`.

## Before starting

- **Name a falsifiable correction objective before touching anything.** Locate
  its region(s), or name the whole frame for a settled palette/light correction.
  An undefined aesthetic goal goes back to direction, not a speculative edit
- **Write the invariants down.** Everything that must not move is stated before
  the edit and restated in every iteration, because drift is cumulative and
  invisible one step at a time
- **Keep the original.** The starting image is an `inputs` entry in the new
  recipe, and it stays on disk until the result is accepted

## Decide first

| Situation | How to proceed |
|---|---|
| Turning a complaint into something a model can act on | [locate-then-change](locate-then-change.md) |
| Choosing how hard a change to make | [edit-ladder](edit-ladder.md) — crop or scale, region edit, extend, re-prompt with invariants, back to the brief; take the lowest rung that can work |
| Picking the edit mode the generator understands | [edit-modes](../reference/edit-modes.md) — the taxonomy the backing skill keys off, and what each preserves |
| A transparent cutout is wanted | [cutouts](../reference/cutouts.md) — chroma key, then local removal, then check the alpha |
| Checking what moved that should not have | [imgfacts](../imgfacts.py) on the before and the after — an edit path can change dimensions or format without saying so |
| The change has failed twice the same way | Stop and hand back. A third attempt at the same rung is how a budget is spent proving nothing |
| A claim here would be expensive to get wrong | [refute](../refute.py) — put it to the engines that did not make it, asked to break it rather than to agree. Unrefuted is n engines finding nothing, never proof |
| The fix would change who or what the picture depicts | That is not a refinement. Hand it back |

## Always / Never

- Always: one falsifiable correction objective per iteration. Coupled changes
  (remove + fill, both hands, several letters) may share a run; check every part
- Always: open the before and the after and say what moved that should not have
- Always: record each retained generative edit as its own recipe with source
  `inputs`; deterministic transforms inherit provenance and record the operation
- Always: get permission first when the edit would alter a person's appearance,
  a brand mark, or anything already published
- Never: describe an edit as applied without opening the result
- Never: carry approval over to a regenerated picture. It can solve the fault,
  but is a new candidate; `IRREPRODUCIBLE` and fresh review still apply
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

## Done when

The fault was located before the change, the invariants held under inspection,
each step has its own recipe naming its source, and the result was opened and
compared rather than assumed.
