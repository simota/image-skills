<!-- image:guidance -->
# Prompt — the request the generator receives

## Owns

The request the generator actually receives — its structure, its exclusions, the
canvas it asks for, and the set of variants that differ on purpose. It decides
what is said, never whether the picture behind it was worth asking for.

Phases: `CLASSIFY → STRUCTURE → CONSTRAIN → SIZE → VARY → RECORD`.

## Before starting

- **Classify the request first.** The backing skill keys its whole behaviour off
  a use-case slug, and a prompt written without one gets classified anyway —
  by the generator, silently, possibly differently each run
- **Read the brief's exclusions.** They become the `Avoid` line verbatim; a
  prompt that restates the inclusions and drops the exclusions has kept the
  easy half
- **Decide what varies before writing variants.** Four prompts differing in ways
  nobody chose produce four results nobody can compare

## Decide first

| Situation | How to proceed |
|---|---|
| Writing the prompt body | [structure](structure.md) — the order that survives: scene, subject, detail, constraint |
| Deciding what to forbid, and how | [exclusions](exclusions.md) — a negative that names a thing beats one that names a feeling |
| Choosing dimensions, or being told a size is invalid | [sizes](../reference/sizes.md) — the four constraints a size must satisfy, and the ones that are known good |
| Checking a canvas before a run is paid for | [imgfacts](../imgfacts.py) `--check-size 1536x1024` — the four constraints, and the nearest legal size when one fails |
| Checking controls, including seed reuse | [control-surface](../reference/control-surface.md) is a snapshot; confirm the selected installed tool/schema before promising a control. A seed routing signal is not seed support |
| Producing variants | Isolating an effect: one axis. Searching for a usable result: coupled axes may vary under one stated objective and budget; do not claim causal attribution |
| Exact text must appear in the image | Quote it verbatim, spell hard words letter by letter, and say where it sits. Then plan to check it against the file — rendered text is where these models fail most visibly |
| A claim here would be expensive to get wrong | [refute](../refute.py) — put it to the engines that did not make it, asked to break it rather than to agree. Unrefuted is n engines finding nothing, never proof |
| A transparent background is wanted | Check the selected tool's current controls. If a cutout is needed, it changes pixels and goes to refinement; a PNG conversion alone cannot remove a background |

## Always / Never

- Always: write the prompt as a labelled spec, not a paragraph. The labels are
  what a later reader diffs when the result changes
- Always: keep the sent text verbatim in the record. A paraphrase is a different
  prompt, and the difference is invisible until someone tries to reuse it
- Always: state invariants for an edit — *change only X, keep Y unchanged* — in
  every iteration, not only the first
- Always: get permission first when the prompt names a living artist, a real
  person, or a brand
- Never: ask the built-in path for a pixel size and treat it as agreed. The
  canvas is a request; what comes back is measured off the file
- Never: pile on adjectives without a correction objective. Related changes
  can share a run; isolate one axis only when the question needs causal comparison
- Never: leave the exclusions to be inferred from the positive description

## Verify with

The prompt is checked against the brief line by line: every axis present, every
exclusion carried, nothing added that the brief did not ask for (evidence:
`inspected` — the prompt is text, and nothing about it can be measured until a
file comes back).

- **The size is checked before it is sent**, not after a run fails: `measured`
  by [imgfacts](../imgfacts.py), which reads those four rules from the registry
- **The record is the recipe's `prompt` field**, verbatim, and the run that uses it
  states `IRREPRODUCIBLE` when exact pixel regeneration is not supported; this
  does not prevent reusing the original file or editing it

## Done when

The use case is named, the spec is labelled, the exclusions are verbatim from
the brief, the size satisfies the applicable constraints, variants name their
objective and changed axes, and the exact text sent is written down.
