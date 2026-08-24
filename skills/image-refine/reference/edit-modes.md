<!-- image:deferred -->
Purpose: the edit taxonomy the backing skill keys off, and what each mode is expected to preserve.
Read when: classifying a change before making it, or an edit preserved the wrong things.
Verified: 2026-08-23 — the slugs are quoted from the installed backing skill's
`SKILL.md`; the preservation notes are from its own guidance plus observed runs.
The note on the second generator's input parameter was read from its own
parameter list on 2026-08-24. No automated check re-reads either installed copy,
so a newer version may add slugs.

# Edit modes

The backing skill classifies every request into a use-case slug and behaves
differently per slug. Naming the slug explicitly means the classification is a
decision rather than a guess made downstream.

**The slugs belong to the pixel generator.** The aspect generator has no slug
vocabulary at all: it takes input images through an `ImagePaths` array and works
out from the prompt what they are for. Everything below still applies to it as
*guidance* — the intent distinction, the invariant list, the per-image role
labels — but as words inside the prompt rather than as a classification the tool
keys off. That makes the role labels load-bearing there rather than helpful.

## Intent first

- The user wants to modify an existing image while preserving parts of it →
  **edit**
- The user supplies images only as style, composition, or mood guidance →
  **generate**
- No images supplied → **generate**

That distinction matters more than the slug: an image handed over as a
*reference* is not an edit target, and treating it as one produces a copy of
the reference rather than a new picture in its manner.

## The edit slugs

| Slug | The change | Expected to preserve |
|---|---|---|
| `text-localization` | Replace or translate in-image text | Layout, typography, everything not text |
| `identity-preserve` | Put a person in a scene, try-on | Face, body, pose |
| `precise-object-edit` | Remove or replace one element | Everything else, including edges around the change |
| `lighting-weather` | Time of day, season, atmosphere | Subject, composition, all geometry |
| `background-extraction` | Cutout, transparent background | The subject and its edges |
| `style-transfer` | Apply a reference style | Subject and scene, in a new manner |
| `compositing` | Insert or merge across images | Lighting and perspective consistency between sources |
| `sketch-to-render` | Line art to render | Composition and the drawn intent |

## Roles for every input image

When more than one image goes in, each one is labelled — reference, edit
target, or supporting insert. An unlabelled second image is a coin toss between
"use this as the subject" and "use this as the style".

```
Image 1: edit target
Image 2: supporting insert — the object to place, upper left
Image 3: reference — lighting only
```

## What the slug does not do

The slug sets expectations; it does not enforce them. `identity-preserve` is a
request to keep a face, not a guarantee, and the check is the same as
everywhere else in this set: open the before and the after and look. The
invariant list is what makes that check possible, and it belongs in the prompt
regardless of slug.

## Local inspection before an edit

If the edit target is only on the local filesystem, view it before editing — the
backing skill needs the image in context, and a run that never saw its target
is editing a description. This is the same rule as everything else here: the
file gets opened.
