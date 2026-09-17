<!-- image:contract -->
# RECIPE — how every image can be accounted for

Binding on every `image-*` skill. A generated image is the one deliverable in
this family that carries no history inside itself: open the file a month later
and there is nothing in it that says what was asked for, what was excluded, or
what it was made from. **This contract makes that history travel beside it.**

## The failure this prevents

A picture lands in a repository. It is fine. Six weeks later it needs redoing
one shade darker, at a second size, or without the logo — and nobody can say
which words produced it. Keep the source as well as its
request: editing the original and generating a new approximation are different
ways to meet that goal, and neither requires pretending to recreate its pixels.

## The seven fields

**The unit is a retained generated candidate**: shown to the user, passed to a
comparison, kept for later use, or used as an edit input. Capture the exact request
at invocation; persist the recipe when the candidate crosses immediate selection.
A direction or prompt-only output owes no future engine, model, output path or
on-disk size. Reading/referencing a supplied image does not create a recipe:
link existing provenance or state supplied/unknown origin, never invent fields.
These non-applicable fields are not `UNSPECIFIED` decisions.

| Field | Means | What must appear |
|---|---|---|
| `engine` | What was invoked | The command, not the vendor. Two generators are in use and they take different arguments; which one ran is the first thing this field settles |
| `model` | What the engine reported using | As reported, or `unreported` if unavailable. A plausible model name is not evidence |
| `prompt` | The text actually sent | Verbatim, including line endings. Short is not evidence of a summary |
| `excluded` | What the request told it to leave out | The exclusions as sent, or `none` |
| `size` | Requested size/aspect and on-disk dimensions | Both; say parameter, prose request or not specified for `asked`, and measure `on_disk` |
| `inputs` | Reference or source images | Path per input, and what each was for |
| `output` | Where the file landed, and where it was copied to | The returned path and retained location; authorized artifact storage is valid |

## `IRREPRODUCIBLE` — the eighth case, and the honest one

For a run without confirmed exact regeneration, the recipe preserves intent,
not identical pixels: state `IRREPRODUCIBLE` once. The registry and references
are snapshots; check the selected installed tool before promising a control.
Seed availability alone does not guarantee identical pixels across model changes.

**The chosen file is the artifact.** Refuse only the unsupported promise of exact
pixel regeneration, not all sameness requests. Reuse/copy an existing original;
"same image, darker background" can be an edit. Same prompt, composition,
identity and visually close recreation are distinct goals, named and inspected
as such. Never spend on a new generation while promising an identical file.

## Recording it

The recipe travels as a block next to the image — a sidecar file, a caption in
the deliverable, or a table row. Link an existing record rather than duplicating
it. Keep provenance accessible to authorized users; it need not be public.
Prefer capture with the returned file and actual generator: a newest-file
timestamp alone cannot bind a cached file to this invocation.

```yaml
engine: "codex exec (image generation)"
model: "<as the run reported it, or unreported>"
prompt: "<verbatim>"
excluded: "<as sent, or none>"
size: { asked: 1536x1024, on_disk: 1536x1024 }   # on_disk read off the file;
                                                 # on the aspect path `asked` is a ratio
inputs: [{ path: brand/mark.png, role: "logo to match" }]
output: { generated: "<generator path>", placed: "assets/hero.png" }
note: IRREPRODUCIBLE — exact regeneration not established; this file is the artifact
```

## Boundary cases

- **A recipe written from memory after the fact** is not a recipe. If the exact
  `prompt` was not kept, say so and mark the image `IRREPRODUCIBLE` on that
  ground too — a remembered prompt is a plausible prompt
- **A retained generative edit is its own recipe**, naming its source as `inputs`.
  Four edits used as a chain need four; an unused discarded edit needs none.
  Deterministic exports inherit provenance and record their transform/result
- **An immediately rejected candidate needs no recipe.** Four made, three
  immediately discarded: one recipe. Four passed to later comparison: four.
  A rejected file kept for possible reuse is retained and needs its recipe.
  Truly discarded work cannot promise later recovery; if its request is lost,
  state unknown origin rather than reconstructing it
- **`size` on disk is `measured` and `size` asked for is not** — the second is
  the request. A recipe that records only the request has recorded a wish
- **Failed/refused calls with no file have no image recipe.** Keep a compact
  attempt/outcome/known-or-unknown-charge entry in the existing run log; reference
  its actual invocation instead of duplicating prompts. Never invent an output
  or quietly reword past a refusal
- **Generation and refinement share spend**, including failed/refused attempts
  unless confirmed uncharged. Calls, candidates, iterations and money differ;
  unknown billing is not zero, and changing skill does not reset the budget
