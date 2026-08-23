<!-- image:deferred -->
Purpose: what this class of generator gets wrong, where it hides, and how to tell a defect from a choice.
Read when: sweeping an image, or a picture reads as wrong and nobody can say why.
Verified: 2026-08-23 — assembled from failures observed in generations run
against the installed backing skill and from its own guidance on validating
output. No automated check re-runs this; a newer model will drop some entries and
add others, and the sites are more durable than the specifics.

# What goes wrong, and where it hides

## Structure and anatomy

| Site | What to look for |
|---|---|
| Hands | Digit count, digit length, thumbs on the wrong side, a hand merging with what it holds |
| Eyes | Mismatched pupils, gaze that does not converge, asymmetric catchlights |
| Teeth | Count, spacing, a smile that is a texture rather than teeth |
| Limb joins | An arm that starts in the wrong place, a second shoulder, a leg that becomes furniture |
| Jewellery, straps, laces | Chains that pass through themselves, a strap that stops mid-shoulder |
| Repeated people | The same face twice in a crowd; background figures without legs |

## Text

The most visible failure and the fastest to spot once looked for. Read every
glyph.

- Letterforms that are letter-*like* — the right rhythm, not the right letters
- Correct first word, degrading rightward
- Doubled or dropped letters in the middle of a long word
- Text in a language the request did not ask for
- A sign, label, or book spine nobody asked to be legible, that is nearly legible

## Physics

These are what "it looks AI-generated" usually means. Nobody names them; almost
everybody feels them.

- Two light sources when the scene has one — check every shadow direction
- Shadows that do not touch the object casting them
- A reflection showing something that is not in front of the surface
- Perspective that holds locally and drifts across the frame
- Scale drift — a background object the wrong size for its distance
- A horizon that changes height behind an occluding object

## Material and surface

- Texture that repeats at a regular interval
- A material that changes partway along a surface
- Fabric with no weight — folds that do not follow gravity
- Over-smooth skin next to a highly detailed background

## Composition

- The subject centred when the brief asked for negative space
- Something important sitting exactly where a crop will cut
- Symmetry the request did not ask for — a strong default, and a strong tell
- A tangent: two edges just touching, which reads as a mistake even to a viewer
  who cannot name it

## Set-level

- Palette or light drifting across members generated from one skeleton
- Subject scale inconsistent between members
- One member in a different medium — the tell that its prompt diverged

## Defect or choice?

Three questions, in order:

1. **Does the brief forbid it?** Then it is a defect, regardless of appearance
2. **Would a viewer at shipping size read it as a mistake?** Then it is a
   defect, whatever the intent was
3. **Is it merely different from what the reviewer would have done?** Then it is
   direction, and it goes upstream rather than being ranked here

## What this catalogue is not

A checklist that finding nothing on means the image is clean. It lists the sites
worth going to deliberately. New failure modes arrive with every model, and the
cold first impression in `seeing` remains the only pass that can catch one
nobody has named yet.
