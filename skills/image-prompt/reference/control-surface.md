<!-- image:deferred -->
Purpose: what each generator actually accepts, so a request does not spend words on levers that do not exist.
Read when: deciding what to put in a prompt, or wondering why an instruction was ignored.
Verified: 2026-08-23 — read off the installed backing skill and confirmed by
running one generation through the default path. The second generator's section
was added 2026-08-24 from one run through it and its own parameter list. Model
names and mode behaviour are a snapshot of one machine; no automated check
re-reads them, and only the aspect list is checked, by `make figures`.

# What the generators will and will not honour

**Two are installed and their surfaces are not the same shape.** One takes
pixels, the other takes a ratio off a fixed list. A prompt written for the wrong
one spends its words on a lever that is not there.

# The pixel generator

The backing skill is Codex's `imagegen`, installed under
`$CODEX_HOME/skills/.system/imagegen/`. It has exactly two modes and they have
very different control surfaces.

## Default: the built-in tool

Invoked as the `image_gen` tool inside a Codex session. No API key. This is the
path almost every request takes.

**What it takes:** a prompt. That is the whole surface.

**What it does not take:** size, quality, output format, output path, a seed, a
transparency flag, a mask. Anything on that list has to be either asked for in
prose inside the prompt — where it is a suggestion — or done afterwards to the
file.

**Where the file lands:** `$CODEX_HOME/generated_images/<id>/exec-<id>.png`. A
project asset is copied out of there; one left behind is one cache clear from
gone.

**Consequences worth planning for:**

- The returned image will not reliably match a requested pixel size. Measure it
- No seed means no repeat. Every run is a new picture from the same request
- Transparency is not a setting. Generate on a flat chroma-key background and
  remove it locally afterwards
- Batches are one call per variant, not one call returning several

## Fallback: the CLI

`scripts/image_gen.py`, with subcommands `generate`, `edit`, `generate-batch`.
Requires `OPENAI_API_KEY`. **It is not the default and it is not for ordinary
size or path control** — the backing skill says so explicitly, and switching
without being asked is a decision made on the user's behalf.

It defaults to `gpt-image-2`, which is also the model the size constraints in
`sizes.md` describe. It exposes what the built-in path does not: model,
`quality`, explicit size, masks, output format, `--out` / `--out-dir`, and
native transparent background on one older model. Reach for it when the user
asks for it, or when a transparency request is too complex for local key
removal — and ask first.

# The aspect generator

The `generate_image` tool built into the `agy` CLI. No API key, no flag, no
second mode: the model calls it because the prompt asked for an image.

**What it takes:** `Prompt`, an `ImageName` for the filename stem, an optional
`AspectRatio` from seven fixed shapes, and optional `ImagePaths` for inputs.

**What it does not take:** a pixel size, a seed, quality, an output path, an
output format, a mask, a transparency flag. `AspectRatio` is the only
dimensional control and there is no smaller or larger version of a shape.

**Where the file lands:** under the CLI's own conversation directory, **as a
JPEG**. Not configurable. A lossless or transparent asset is a conversion made
afterwards, and it is a second operation on the image.

**Consequences worth planning for:**

- A shape not on the list is unavailable, not approximate. Compose for one that
  is, and crop
- No seed here either. Every run is a new picture from the same request
- The run can report an error while having written the file. Look in the
  directory rather than believing the envelope
- Batches are one call per variant, same as the other path

## What controls the picture, in order of effect

Given surfaces this small, the prompt is doing nearly all the work on either
generator, and the list below does not change between them.

1. **Subject and action** — the largest single lever, and the one most often
   under-specified
2. **Medium** — photograph, illustration, 3D render. Changes everything
   downstream of it
3. **Light** — direction and hardness. The strongest control over mood
4. **Framing and camera position** — and, for photographs, lens language
5. **Palette** — as physical description, not as a mood word
6. **Exclusions** — the only lever that reliably *removes* something
7. **Repetition of an invariant** — for edits, the main defence against drift

Anything not on that list is being asked for by hope.
