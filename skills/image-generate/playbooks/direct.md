<!-- image:guidance -->
# Direct — what the picture must say

## Owns

What the picture is for, what it must say, and what it should look like saying
it. It produces a brief a generator can be aimed at and a reviewer can judge
against — never the wording that gets sent, and never a picture.

Phases: `PURPOSE → SURVEY → REFERENCE → DECIDE → BRIEF`.

## Before starting

- **Open what already exists.** The product's current images are the standard
  unless someone decides otherwise, and a direction written without looking at
  them is a second visual system nobody agreed to
- **Name the surface.** A hero, an avatar, an OG card and a spot illustration
  want different subjects at different crops. A brief that does not say where
  the picture lands cannot say whether it worked
- **Say what the picture must not be.** Exclusions are the only part of a brief
  a downstream stage can check itself against

## Decide first

| Situation | How to proceed |
|---|---|
| A reference image or product was handed over | [reference-reading](reference-reading.md) — take the principle, name it, and say what was deliberately not copied |
| Deciding what is in frame and how it sits | [subject-and-frame](subject-and-frame.md) |
| Writing the brief itself | [direction-brief](../reference/direction-brief.md) — the fields, and what an empty one means |
| Choosing words that will survive into a prompt | [style-vocabulary](../reference/style-vocabulary.md) — which descriptions move an image model and which are decoration |
| Describing what the direction departs from | [imgfacts](../imgfacts.py) — dimensions, format and colour read off the existing files, so `baseline` is measured rather than recalled |
| The request is "make it look better" | Not executable. Settle what better means against the current image, in the dialogue, before anything else |
| The product has no images at all | Say so. The brief's `standard` is then a stated intent, not a precedent, and every downstream stage inherits that difference |
| A claim here would be expensive to get wrong | [refute](../refute.py) — put it to the engines that did not make it, asked to break it rather than to agree. Unrefuted is n engines finding nothing, never proof |
| The picture would depict a real person, product or organisation | Stop. That is the human's decision, and it is not reversible once published |

## Always / Never

- Always: state the one thing the picture has to communicate, in a sentence,
  before anything about how it looks
- Always: write the exclusions with the inclusions. "Warm, human, unposed" and
  "no stock-photo handshakes, no glass buildings" are one decision
- Always: name the crop the picture has to survive — a hero cropped square on
  mobile is two compositions
- Always: get permission first when the direction departs from the product's
  existing images, when a named artist's style is invoked, or when a real
  person, product or organisation would appear
- Never: hand over a mood without a subject. A generator will invent one
- Never: copy a reference's identity — take the principle and say what you left
- Never: decide the pixel dimensions here. That is the request's business, and
  the generator has its own constraints
- Never: settle a direction against a picture nobody opened

## Verify with

The current images were opened and described, and the brief's `baseline` says
what they are (evidence: `measured` — a look at the files, not a memory of
them). A direction whose baseline is recalled is `asserted` and reads exactly
like one that was checked.

- **Every axis has an achievement condition.** Read each one back and ask what
  would falsify it. "Warm, no gradients, one focal point" survives that
  question; "modern" does not
- **The brief is `IRREPRODUCIBLE`-aware**: it fixes intent, and intent is all a
  generator without confirmed exact regeneration can be held to

## Done when

The purpose is one sentence, the standard names something that exists or is
declared a stated intent because nothing exists, every axis can be falsified,
the exclusions are non-empty, and the brief says where the picture lands and at
what crops.
