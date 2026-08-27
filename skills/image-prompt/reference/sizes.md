<!-- image:deferred -->
Purpose: what size each generator will accept — pixel canvases for one, a fixed list of aspects for the other — and which are known to work.
Read when: choosing dimensions, or a run has been rejected for an invalid size.
Source: none — nothing outside this page can move what it states.
Verified: 2026-08-23 — the constraints and the size list are quoted from the
installed backing skill; the aspect list was re-read from the running tool on
2026-08-24 and one 1:1 run measured. `make figures` recomputes every row below
against those constraints, and checks both the four constraints and the aspect
list against `registry/harness.yaml`, which is what `imgfacts.py` decides
legality from — so the page, the tool and the build cannot disagree. What
nothing re-checks is either backing tool: both are a snapshot of one installed
copy, and the models they belong to are named in `control-surface.md`.

# Sizes

**The two generators do not take the same argument, and one of them takes no
pixel size at all.** Which one is running decides what the paragraph below is
even about; `control-surface.md` is where they are set side by side.

# Canvas sizes — the pixel path

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

# Aspects — the ratio path

The other generator's `generate_image` takes `AspectRatio` and nothing else: no
width, no height, no megapixel count. **The seven below are the whole size
surface**, and a shape not on the list is not a smaller request — it is a
request that cannot be made.

| Aspect | What it is for |
|---|---|
| `1:1` | square; the one measured run came back 1024x1024 |
| `2:3` | portrait |
| `3:2` | landscape |
| `3:4` | portrait, closer to square |
| `4:3` | landscape, closer to square |
| `9:16` | tall, full-bleed on a phone |
| `16:9` | widescreen |

`imgfacts.py --check-aspect 5:4` answers whether a shape is on the list, and
when it is not it names the nearest one that is. It reduces what it is given
first, so `1920:1080` and `16:9` are the same question.

Two consequences the pixel path does not have:

- **The returned dimensions are whatever that aspect returns.** They are read
  off the file, and the recipe records the aspect asked for beside them — there
  was no pixel count to record
- **A size larger than what comes back is an upscale afterwards**, not a
  different request. Plan the delivery rungs from the measured file

## Choosing one

- **Ask for the aspect the picture is composed for**, not the aspect of the
  container it lands in. Cropping down is free; cropping up is a new picture
- **Do not ask for the shipping size.** The largest useful size is a source
  file, and every derived size is emitted from it downstream
- **A ratio beyond 3:1 is not available.** A very wide banner is generated at
  the widest legal ratio and cropped, or composed as two pictures
