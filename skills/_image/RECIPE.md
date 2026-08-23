<!-- image:contract -->
# RECIPE — how every image can be accounted for

Binding on every `image-*` skill. A generated image is the one deliverable in
this family that carries no history inside itself: open the file a month later
and there is nothing in it that says what was asked for, what was excluded, or
what it was made from. **This contract makes that history travel beside it.**

## The failure this prevents

A picture lands in a repository. It is fine. Six weeks later it needs redoing
one shade darker, at a second size, or without the logo — and nobody can say
which words produced it. The options are to start over and accept that the new
one will not match, or to keep a picture nobody can change.

**The wording is the asset.** The file is what the wording happened to return.

## The seven fields

Every image an output points at carries all seven. A blank is a field nobody
decided, not one that does not apply.

| Field | Means | What must appear |
|---|---|---|
| `engine` | What was invoked | The command, not the vendor — `codex exec` with image generation enabled |
| `model` | What the engine reported using | As reported. Recalled from habit is not reported |
| `prompt` | The text actually sent | Verbatim. A paraphrase is a different prompt |
| `excluded` | What the request told it to leave out | The exclusions as sent, or `none` |
| `size` | Pixels asked for, and pixels on disk | Both. They disagree more often than anyone expects |
| `inputs` | Reference or source images | Path per input, and what each was for |
| `output` | Where the file landed, and where it was copied to | The generator's own path and the project path |

## `IRREPRODUCIBLE` — the eighth case, and the honest one

The generator this set uses exposes no seed. Running the same recipe again does
not return the same image; it returns another image from the same request.

So a recipe fixes the **intent** and never the pixels, and the gap is stated,
once, in the handoff — `IRREPRODUCIBLE`. It is not a residual and it is not a
defect. It is what this generator is.

Two things follow. **The chosen file is the artifact**, not the recipe, so the
file is kept and versioned rather than regenerated on demand. And **a request
for an exact reproduction is refused with the reason**, not attempted: a
near-match returned as "regenerated" is the most expensive lie in this set,
because the difference is visible to everyone except the transcript.

## Recording it

The recipe travels as a block next to the image — a sidecar file, a caption in
the deliverable, or a table row. The form is not the point; the field being
impossible to leave blank is.

```yaml
engine: "codex exec (image generation)"
model: "<as the run reported it>"
prompt: "<verbatim>"
excluded: "<as sent, or none>"
size: { asked: 1536x1024, on_disk: 1536x1024 }   # both, read off the file
inputs: [{ path: brand/mark.png, role: "logo to match" }]
output: { generated: "<generator path>", placed: "assets/hero.png" }
note: IRREPRODUCIBLE — no seed; this file is the artifact
```

## Boundary cases

- **A recipe written from memory after the fact** is not a recipe. If the exact
  `prompt` was not kept, say so and mark the image `IRREPRODUCIBLE` on that
  ground too — a remembered prompt is a plausible prompt
- **An edit is its own recipe**, with the image it started from as an `inputs`
  entry. A chain of four edits is four recipes, not one
- **A rejected candidate needs no recipe.** The one that ships does, and so does
  any candidate a later stage is asked to compare against
- **`size` on disk is `measured` and `size` asked for is not** — the second is
  the request. A recipe that records only the request has recorded a wish
- **A prompt the generator refused, then a reworded one that worked**, is two
  entries. Keeping only the second hides the constraint from everyone after you
