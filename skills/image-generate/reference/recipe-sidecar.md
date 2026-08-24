<!-- image:deferred -->
Purpose: the form a recipe travels in, and where to put it so it survives.
Read when: recording a run, or picking up an image whose origin is unknown.
Verified: 2026-08-23 — no automated check reads this page. `recipe.py` writes
and validates the shape below, and `image-tools/test_tools.py` round-trips it and
proves each field is required, so the *shape* has a check; this page's prose,
the placement conventions and this copy of the field list do not.

# Writing a recipe down

`_image/RECIPE.md` fixes *what* is recorded. This page is about *where*, and
about the forms that survive contact with a real repository.

**Do not hand-write one.** `recipe.py capture` takes the newest file a generator
left, places it where the project wants it, and writes the sidecar with the size
read off the file rather than the size the prompt asked for:

```sh
recipe.py capture --to assets/hero.png --prompt-file p.txt \
  --excluded "watermarks, text" --asked 1536x1024
recipe.py capture --to assets/hero.jpg --prompt-file p.txt \
  --generator agy --asked 16:9        # the aspect path: a ratio, never pixels
recipe.py check assets/hero.png        # every field, and the size against the file
recipe.py check --dir assets/          # and which images have no recipe at all
```

`--generator` picks whose output directory is searched and whose invocation goes
into `engine`. Without it, every declared generator's directory is searched and
the newest file across all of them wins — a timestamp, rather than a guess about
which CLI is running.

It refuses to overwrite an existing file: that is a sibling-version decision for
a person (`naming` in the delivering skill), not something a tool does quietly.

## The three forms

**A sidecar file** — `hero.png` beside `hero.png.recipe.yaml`. Best when images
live in the repository and will be edited again. Survives file moves badly;
survives everything else well.

**A manifest** — one `images.yaml` per directory, keyed by filename. Best for a
set generated together. One file to read, one file to conflict on.

**In the deliverable** — a block in the document, spec, or pull request that
introduces the image. Best for a one-off that will never be regenerated. It is
the form most likely to be lost, and it is honest about that.

Pick one per project and keep it. Two conventions in one repository means every
future reader checks both.

## The shape

```yaml
engine: "codex exec --enable image_generation"
model: "<as the run reported it, or unreported>"
prompt: |
  Use case: product-mockup
  Asset type: docs landing header
  Primary request: a worn wooden desk at dusk, one warm lamp from the right
  Composition/framing: three-quarter view, standing height, upper third empty
  Avoid: watermarks, text, people, logos
excluded: "watermarks, text, people, logos"
size: { asked: "1536x1024 (in prose; the path takes no size argument)",
        on_disk: "1254x1254" }
inputs: []
output:
  generated: "~/.codex/generated_images/01a0…/exec-d9e8….png"
  placed: "docs/assets/landing-header.png"
note: "IRREPRODUCIBLE — no seed. This file is the artifact."
```

## The fields people get wrong

- **`prompt`** is the text *sent*, not the text meant. Use a block scalar so the
  labelled lines survive intact. A one-line summary is not a prompt
- **`model`** is what the run reported. If it reported nothing, write
  `unreported` — that is information, and a plausible model name is not
- **`size.asked`** says which path was used as much as it says a number: on the
  pixel generator's default path the size was a sentence in the prompt, and on
  the aspect generator it is a ratio and there was never a pixel count to ask
  for. Either way it explains any disagreement with `on_disk`
- **`output.generated`** is kept even after the file is copied. It is how a
  later reader tells a generated asset from a hand-made one
- **`inputs`** is empty for a fresh generation and never empty for an edit

The same run on the aspect generator differs in three fields, and in nothing
else:

```yaml
engine: "agy --print"
size: { asked: "16:9 (the whole size surface; it takes no pixel count)",
        on_disk: "1024x1024" }
output:
  generated: "~/.gemini/antigravity-cli/brain/a0a5…/landing-header_1787….jpg"
  placed: "docs/assets/landing-header.jpg"
```

A `.jpg` extension on `placed` is not an oversight: that path writes JPEG and a
PNG beside it is a conversion, which is its own operation and its own line in
the recipe.

## A chain of edits

Each edit is its own recipe, and its `inputs` names the file it started from.
Four edits are four recipes. Collapsing them into one loses the order, and the
order is the only thing that explains the result.

```yaml
- output: { placed: "hero-v1.png" }
  inputs: []
- output: { placed: "hero-v2.png" }
  inputs: [{ path: "hero-v1.png", role: "edit target" }]
  prompt: "change only the background to a warm gradient; keep the desk, the
           lamp and the crop unchanged"
```

## When there is no recipe

An image found in a repository with no recipe is recorded as such — `origin:
unknown` — rather than given a reconstructed one. A remembered prompt is a
plausible prompt, and the difference between plausible and actual is the whole
value of the field.
