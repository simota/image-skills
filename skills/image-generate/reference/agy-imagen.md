<!-- image:deferred -->
Purpose: how to invoke the aspect-ratio generator, what its tool takes, where the file lands, and the two things about it that surprise people.
Read when: generating on this path, or a run reported an error while leaving a file behind.
Source: agy — the flags and defaults below are that CLI's, and move with its releases.
Verified: 2026-08-24 — every claim below was produced by running one generation
on macOS and reading the run's own transcript and the file it wrote; the
parameter list was re-read from the running tool. The aspect list is re-checked
by `make figures` against the registry. Nothing re-reads the tool
itself, so the rest is a snapshot of one installed copy on one machine.

# Invoking the aspect-ratio generator

The generator is the `generate_image` tool built into the `agy` CLI. This set
does not reimplement it and does not call an image API directly.

## From outside a session

```sh
agy --print="<the labelled prompt spec>" --output-format json
```

The model decides to call `generate_image`; there is no flag that calls it
directly and no flag that enables it. Say in the prompt that an image is wanted,
and **ask explicitly for the absolute path of the file** — the tool's own result
text tells the model not to print the path, so a run that is not asked will not
volunteer it.

`--dangerously-skip-permissions` is what an unattended run needs; without it a
permission prompt has nobody to answer it.

## What the tool takes

| Parameter | Required | What it is |
|---|---|---|
| `Prompt` | yes | the request, and nearly the whole control surface |
| `ImageName` | yes | the stem of the filename, not a caption |
| `AspectRatio` | no | one of seven fixed shapes, listed in the registry |
| `ImagePaths` | no | input images: edit targets or references |

**There is no size, no seed, no quality, no output path, no format, no mask.**
`AspectRatio` is the entire dimensional lever, and everything else is prose
inside `Prompt` where it is a suggestion.

## Where the file lands

```
~/.gemini/antigravity-cli/brain/<conversation-id>/<ImageName>_<epoch-ms>.jpg
```

**It is a JPEG.** Not a PNG, and there is no flag that makes it one: the
measured run wrote 1024x1024, 84,045 bytes, no alpha channel, no colour profile
declared. Anything needing transparency or lossless pixels is a conversion
afterwards, and a conversion is a second operation on the image that belongs in
the recipe as one.

**Nothing cleans this directory up and nothing guarantees it survives.** A file
the project will reference is copied out — `recipe.py capture --generator agy`
is that copy-out, and it writes the recipe in the same move.

## The two behaviours that surprise people

- **The run can report `status: ERROR` with the image sitting on disk.** The
  observed run ended `"status":"ERROR","error":"no image generated in
  response"` and had written a complete 84KB JPEG. The status describes the
  final message, not the filesystem. **Open the directory before believing the
  envelope** — and equally, a `SUCCESS` is not evidence a file exists
- **A first call can be abandoned and retried under a different `ImageName`.**
  The observed run called the tool twice; only the second left a file. So the
  newest file is the answer, and the count of calls is not the count of images

## Cost and time

The measured run took 34 seconds end to end, ten of them inside the tool. One
call, one image; a batch is several calls. The run reports token usage and not
an image price, so spend against a budget is counted in calls here.
