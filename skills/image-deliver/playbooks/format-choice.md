<!-- image:guidance -->
# Choosing a format

The format follows what is *in* the picture, not what the project usually does.
A photograph and a flat illustration compress by opposite mechanisms, and
picking by habit costs either bytes or visible damage.

## What is in the picture decides

| The picture is | Format | Why |
|---|---|---|
| A photograph or a render — continuous tone, noise, gradients | Lossy, quality around 75–85 | Lossless spends bytes preserving noise nobody can see |
| Flat colour, few tones, hard edges, any lettering | Lossless | Lossy encoders put visible mush around a hard edge |
| Anything needing real transparency | Lossless with alpha | Alpha in a lossy format is patchy support and patchy quality |
| A photograph *with* transparency | Modern lossy with alpha, and check it | The one genuinely awkward case. Verify the edge |
| An animation | Not this stage's problem. Hand it back | A still-image pipeline will do the wrong thing to it |

## Modern formats

A modern format at the same visual quality is meaningfully smaller than the
older one it replaces. Use it **when the project already ships it** — a build
that handles one format and receives another is a broken image, and the saving
was not worth it.

Where the project handles several, emit the modern one and a fallback, and let
the markup choose. Where it handles one, emit that one and record the saving
that was not taken.

## Quality is chosen by looking

There is no correct number. The procedure is: encode, open both, look at the
worst region — a smooth gradient, a hard edge, a dark area — and step until the
damage is invisible at shipping size.

**Then record the number you landed on, and the byte size.** A quality setting
with no recorded result is a number carried forward until nobody remembers
whether it was chosen.

## The budget

A budget is a number in the brief, not a feeling: *this header is worth under
200KB*. When the encode lands over it, the choices are a smaller pixel size, a
lower quality, a different format, or an explicit decision to exceed it. All
four are fine. **Quietly raising the budget is not.**

## Never re-encode a lossy file

Each generation of lossy encoding compounds the damage of the last, and it is
irreversible. Derive every output from the source, which is kept at full size
and full quality in the repository. If the only copy available is already lossy,
say so — the result is what it is, and the record explains why.

## The checks

- Every emitted file opened, and its format, dimensions and byte size read off it
- The worst region compared against the source at shipping size
- The budget stated, and what each file actually came in at
- Transparency, where it exists, verified in the alpha channel rather than by
  the file looking right against white
