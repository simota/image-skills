<!-- image:deferred -->
Purpose: how to invoke the generator, what each mode takes, where the file lands, and what the invocation cannot do.
Read when: about to generate, or a run behaved differently from what the prompt asked for.
Source: codex — the flags and defaults below are that CLI's, and move with its releases.
Verified: 2026-08-23 — the invocation, the exit behaviour and the output path
were confirmed by running one generation on macOS with the installed skill. The
mode rules and the model defaults are quoted from that installed copy; nothing
re-runs those, so treat them as a snapshot of one machine.

# Invoking the generator

The generator is Codex's own `imagegen` skill, installed at
`$CODEX_HOME/skills/.system/imagegen/` (that is `~/.codex/skills/.system/imagegen/`
unless `CODEX_HOME` is set). This set does not reimplement it and does not call
an image API directly.

## From outside a Codex session

```sh
codex exec --enable image_generation "<the labelled prompt spec>"
```

`--enable image_generation` is equivalent to `-c features.image_generation=true`.
The feature is off by default; a user who has set `image_generation = true` in
`~/.codex/config.toml` does not need the flag, and passing it anyway is harmless
and makes the run self-describing.

Useful additions:

- `-i <file>...` attaches input images to the initial prompt — reference images
  for a generate, or the target of an edit
- `--skip-git-repo-check` when running outside a repository
- `--sandbox workspace-write` if the run also has to copy the result somewhere

The command prints its reasoning and its shell calls; the last line is the
agent's answer. Ask it, explicitly, to end by printing the absolute path of the
file it produced — otherwise the path is buried in the transcript.

## From inside a Codex session

The `image_gen` tool is called directly. Same behaviour, same output location,
no flag needed once the feature is on.

## Where the file lands

```
$CODEX_HOME/generated_images/<session-id>/exec-<call-id>.png
```

**Nothing cleans this up and nothing guarantees it survives.** A file the
project will reference is copied out; one left there is one cache clear from
gone. The backing skill states this as a rule, and it is the single most common
way an image task ends up half-done.

`recipe.py capture` is the copy-out, and it writes the recipe in the same move —
see `recipe-sidecar.md`. Doing it by hand is how the recipe gets written later,
from memory, which `_image/RECIPE.md` calls not a recipe at all.

## What the invocation does not accept

No size, no seed, no quality, no output path, no transparency flag, no mask.
Those exist only on the fallback CLI path, which needs `OPENAI_API_KEY` and is
not entered without asking. The full surface is in the backing skill's own
`references/cli.md` and `references/image-api.md`, under the install path above.

A sibling page in this set covers the same ground for prompt writing, but it is
not linked from here: a relative path out of one skill directory into another
resolves only when both happen to be installed, and a pack may carry one
without the other.

## Observed behaviour worth knowing

- **A requested pixel size is not honoured on the default path.** One run asking
  for 1024×1024 returned a 1254×1254 file. The dimensions are read off the file
  every time — `imgfacts.py <path>` is the shortest way to do it
- **The agent may resize for you.** Asked for an exact size, it may run a local
  resampler after generating. That is a second operation on the image, and it
  belongs in the recipe as one
- **One call, one image.** A batch is several calls, not one call with a count
- **A refusal is an answer.** It is reported as `BLOCKED`, with the refusal text

## Cost and time

Each call is billed and takes tens of seconds. Square is typically fastest.
There is no dry run, so the cheapest way to test a prompt is a small square
draft, not a full-resolution final.
