<!-- image:deferred -->
Purpose: which canvas sizes the generator accepts, the four constraints a size must satisfy, and the ones known to work.
Read when: choosing dimensions, or a run has been rejected for an invalid size.
Verified: 2026-08-23 — the constraints and the size list are quoted from the
installed backing skill. `make figures` recomputes every row below against those
constraints, and checks the four constraints themselves against
`registry/harness.yaml`, which is what `imgfacts.py` decides legality from — so
the page, the tool and the build cannot disagree. What nothing re-checks is the
backing skill itself: the constraints are a snapshot of one installed copy, and
the model they belong to is named in `control-surface.md`.

# Canvas sizes

## The two paths do not take the same argument

**The default built-in path takes no size argument at all.** It is prompt in,
image out. Anything about dimensions is a request inside the prompt text, and
it is routinely not honoured — asking for 1024×1024 returned a 1254×1254 file.
Plan for a resize downstream, and record both numbers in the recipe.

**The fallback CLI path takes an explicit size**, and that is where the
constraints below apply. It is not the default and it needs an API key.

## The four constraints

`imgfacts.py --check-size 1536x1024` answers this, and when the answer is no it
names the nearest legal canvas that is **still the same shape** — aspect is the
constraint, area is what gets minimised, and the tolerance is 0.5%. It reads the
numbers from `registry/harness.yaml`, the same block this page is checked
against.

A size is legal only if all four hold:

1. Maximum edge is 3840px or less
2. Both edges are multiples of 16
3. The long-to-short ratio is 3:1 or less
4. Total pixels are between 655,360 and 8,294,400 inclusive

`auto` is also accepted and lets the model choose.

## Sizes known to be legal

| Size | Ratio | Megapixels | Use |
|---|---|---|---|
| `1024x1024` | 1:1 | 1.05 MP | fast square draft; the cheapest useful run |
| `1536x1024` | 3:2 | 1.57 MP | landscape default |
| `1024x1536` | 2:3 | 1.57 MP | portrait default |
| `2048x2048` | 1:1 | 4.19 MP | square, print-ish |
| `2048x1152` | 16:9 | 2.36 MP | widescreen without paying for 4K |
| `3840x2160` | 16:9 | 8.29 MP | 4K landscape; sits exactly on the pixel ceiling |
| `2160x3840` | 9:16 | 8.29 MP | 4K portrait |

Square is typically fastest. Start there while the prompt is still moving, and
pay for the final aspect once it has stopped.

## Sizes that are rejected, and by which rule

| Size | Breaks |
|---|---|
| `1000x1000` | multiple of 16 |
| `512x512` | total pixels |
| `3840x1024` | ratio |
| `4096x2304` | max edge |

Each of these is recomputed too: if a rule stops being violated by the size
listed against it, the check fails rather than passing quietly.

## Choosing one

- **Ask for the aspect the picture is composed for**, not the aspect of the
  container it lands in. Cropping down is free; cropping up is a new picture
- **Do not ask for the shipping size.** The largest useful size is a source
  file, and every derived size is emitted from it downstream
- **A ratio beyond 3:1 is not available.** A very wide banner is generated at
  the widest legal ratio and cropped, or composed as two pictures
