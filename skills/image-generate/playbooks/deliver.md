<!-- image:guidance -->
# Deliver — from a chosen picture to a file the project uses

## Owns

The distance between a chosen picture and a file the project can use — format,
the sizes the surface needs, compression, colour, name, placement, catalog, and text
that stands in for it when it does not load. It changes files, never pictures.

Phases: `TARGET → EXPORT → NAME → PLACE → DESCRIBE → CATALOG`.

## Before starting

- **Read the target and project policy.** Match storage, naming and formats.
  If the approved asset already satisfies them, use it as-is: no automatic
  re-encode, metadata rewrite, duplicate export or repository copy
- **Get the picture out of the generator's directory first.** A project asset
  living only in the generator's own output folder is one cache clear from gone
- **Know the surface's real dimensions.** A number chosen because the container
  is that wide is this stage's; a number chosen to give the model room was the
  request's, and the two are rarely the same

## Decide first

| Situation | How to proceed |
|---|---|
| Choosing a format and a compression level | [format-choice](format-choice.md) — decided by what is in the picture, not by habit |
| Naming files and variants | [naming](naming.md) — a name that survives a second version and a second size |
| Emitting the set of sizes a surface needs | [export-targets](../reference/export-targets.md) — the scale rungs, and what each one is derived from |
| Metadata needs changing under publication/privacy policy | [strip](../strip.py) reports first. Preserve rendering properties; credentials and other metadata follow project policy, not an automatic export step |
| Colour looks wrong once it is in the page | [colour-and-metadata](../reference/colour-and-metadata.md) — profile, stripping, and what must not be stripped |
| Writing the text that replaces the image | [alt-text](../reference/alt-text.md) — what it is for decides what it says |
| Checking emitted files and provenance | [imgfacts](../imgfacts.py) for file properties, visual viewing for pixels, and [recipe](../recipe.py) checks only retained generated candidates, not unrelated photographs |
| Delivering or updating an image set | [asset-catalog](../reference/asset-catalog.md) — run [catalog](../catalog.py) after placement and link the HTML catalog; emit JSON when a consumer needs it |
| The chosen picture is smaller than the surface needs | Do not upscale it here. Hand it back — a resample is a change to the picture |
| A claim here would be expensive to get wrong | [refute](../refute.py) — put it to the engines that did not make it, asked to break it rather than to agree. Unrefuted is n engines finding nothing, never proof |
| No convention exists in the project | Emit one format and one naming rule, write both down, and say it is now the precedent |

## Always / Never

- Always: open every file you wrote and read its dimensions, format and byte
  size off it. An export pipeline that reports its own intent is reporting a wish
- Always: preserve the source under the project's authorized retention policy
  (artifact storage, LFS, or repository); a git copy is not mandatory
- Always: state the compression budget and what each file actually came in at
- Always: generate or refresh the asset catalog from the final files, following
  project access policy; link recipes without copying their prompts into the catalog
- Always: get permission first before replacing an image already referenced,
  before deleting an original, and before adding a format the project's build
  does not already handle
- Always: write a sibling unless replacement is authorized and rollback is
  verified. Stable URLs and version-controlled replacements may keep the path
- Never: strip colour metadata without checking what the surface assumes
- Never: lose a retained generated candidate's recipe. Keep its provenance
  accessible, not necessarily public; `IRREPRODUCIBLE` does not apply to a copy
- Always: supply the alt decision and context for each known use; the markup
  owner verifies final semantics. Unknown future use has no universal asset-level alt

## Verify with

Every emitted file is opened and its dimensions, format and byte size read off
it (evidence: `measured`), and every reference to it in the project is followed
to make sure it resolves.

- **Sizes are recomputed, not restated**: each derived size follows from the
  source and a stated rung, and both numbers appear
- **Budget overruns are reported as themselves**, not absorbed by quietly
  raising the budget

## Done when

Every file is opened and measured, naming follows the project, the source is kept,
each reference resolves, recipes remain accessible, and the asset catalog is current.
Every known use has a context-specific alt decision or reason it needs none.
