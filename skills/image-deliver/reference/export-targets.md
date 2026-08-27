<!-- image:deferred -->
Purpose: the sizes a surface actually needs, and the rule each one is derived by.
Read when: emitting more than one size, or deciding what the source has to be.
Source: none — nothing outside this page can move what it states.
Verified: 2026-08-23 — every emitted size in the table is recomputed from its own
stated base and factor by `make figures`, so a number edited into a wrong one
fails the build rather than ageing quietly.

# Export targets

## One source, everything derived

The picture is kept once, at full size, at full quality, in the repository.
Every shipped file is derived from it by a stated rule. Deriving from a derived
file compounds encoding damage and loses the ability to re-emit at a new size.

## Density rungs

The base is the CSS box the image occupies. Each rung is that box multiplied by
its factor.

| Rung | Base | Factor | Emitted |
|---|---|---|---|
| `@1x` | 768x512 | 1.0 | 768x512 |
| `@1.5x` | 768x512 | 1.5 | 1152x768 |
| `@2x` | 768x512 | 2.0 | 1536x1024 |
| `@3x` | 768x512 | 3.0 | 2304x1536 |

Source must be at least: 2304x1536

**Emit the rungs the project uses, not all four.** `@1x` and `@2x` covers most
of the web; `@3x` is for surfaces that are actually on high-density displays and
costs its bytes on every other one.

## Choosing the base

The base is the CSS box, measured — the container's width at the breakpoint
that matters, not the width of the design mockup and not the width the model
was asked for. A base guessed from a mockup is the most common reason a shipped
image is either soft or four times the bytes it needed.

## When a surface has a fixed pixel size

Some do — an OG card, an app icon set, a favicon. Those are not derived from a
CSS box; they are fixed numbers set by whatever consumes them, and each one is
looked up rather than reasoned about. Emit exactly what is specified, and check
the emitted file's dimensions against the specification.

## Never scale up

If the source is smaller than the largest rung, the rungs above it are not
available. Do not resample upward here — it is a change to the picture, not an
export, and it belongs to the stage that owns pictures. Say what was available
and hand the gap back.

## What travels with the set

- The source, kept
- Each emitted file, with its dimensions, format and byte size read off it by
  `imgfacts.py` — an export pipeline that reports its own intent reports a wish
- The rule each was derived by — base and factor, so a fifth size can be added
  later without guessing
- The recipe of the original generation, which the export does not replace
