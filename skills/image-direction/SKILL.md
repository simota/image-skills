---
name: image-direction
description: "Deciding what a picture must say before anything is generated: subject and mood, art style, visual reference, composition intent, and the image brief. Use when the look is not settled."
allowed-tools: Read, Grep, Glob, Bash, Write
---
<!-- image:contract -->

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
<!-- deliver:sizing -->
- **Size it before anything else**, first match wins. `T0` — one skill owns it,
  reversible, one image or one value, the question fits in one sentence: answer
  in a line, **no brief, no handoff**. `T1` — a `T0` condition fails: settle the
  brief first. `T2` — two or more skills own parts of it: route it. `T0` drops
  the paperwork, never the evidence. Mis-sized mid-run means re-sizing and saying so
- **A dialogue comes first** when the deliverable's shape is not uniquely
  determined, what counts as achieved does not fit in one sentence, the request
  carries a word with no achievement condition ("nicer", "cleaner", "premium",
  "more professional"), or the work replaces a picture a person already chose.
  Looking at what exists is not executing
- **Settle `standard` in that dialogue** — what the image is judged against.
  Without one, every candidate is arguable and the loop has no exit. `excludes`
  may not be empty and execution waits on an empty `open_questions`
  (`_image/SIZING.md`)
<!-- /deliver:sizing -->
<!-- deliver:recipe -->
- **Every image an output names carries its recipe.** `engine`, `model`,
  `prompt` verbatim, `excluded`, `size` asked for and size on disk, `inputs`,
  `output` path — the run is written down, not remembered, and `engine` says
  which of the two generators ran. Neither exposes a seed, so a recipe fixes the
  intent and never the pixels: that gap is `IRREPRODUCIBLE`, stated once in the
  handoff and never papered over with a seed nobody has (`_image/RECIPE.md`)
<!-- /deliver:recipe -->

## Decide first

| Situation | How to proceed |
|---|---|
| A reference image or product was handed over | [reference-reading](playbooks/reference-reading.md) — take the principle, name it, and say what was deliberately not copied |
| Deciding what is in frame and how it sits | [subject-and-frame](playbooks/subject-and-frame.md) |
| Writing the brief itself | [direction-brief](reference/direction-brief.md) — the fields, and what an empty one means |
| Choosing words that will survive into a prompt | [style-vocabulary](reference/style-vocabulary.md) — which descriptions move an image model and which are decoration |
| Describing what the direction departs from | [imgfacts](imgfacts.py) — dimensions, format and colour read off the existing files, so `baseline` is measured rather than recalled |
| The request is "make it look better" | Not executable. Settle what better means against the current image, in the dialogue, before anything else |
| The product has no images at all | Say so. The brief's `standard` is then a stated intent, not a precedent, and every downstream stage inherits that difference |
| A claim here would be expensive to get wrong | [refute](refute.py) — put it to the engines that did not make it, asked to break it rather than to agree. Unrefuted is n engines finding nothing, never proof |
| The picture would depict a real person, product or organisation | Stop. That is the human's decision, and it is not reversible once published |
<!-- deliver:values -->
- Ties break by `_image/VALUES.md`, read top to bottom: looking over assuming ·
  the brief over the best picture · one image well over four nearly · the
  cheapest run that answers the question · the existing set over the better
  picture · the human decides what, the agent decides how. Against all of them:
  **a harness that is correct and avoided has failed** — when the ceremony costs
  more than the decision, say so rather than performing it
<!-- /deliver:values -->

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
  would falsify it. "Modern" survives that question; "warm, no gradients, one
  focal point" does not
- **The brief is `IRREPRODUCIBLE`-aware**: it fixes intent, and intent is all a
  seedless generator can be held to
<!-- deliver:report -->
- **Grade every claim**: `measured` (the file was opened and the property read
  off it) supports completion; `inspected` (opened and reasoned over, nothing
  measured) only where nothing can be measured and the entry says why;
  `asserted` never does. **A property taken from the request is `asserted`** —
  the prompt asked for 3:2, it does not report what came back
- **The unit is the decision, not the batch.** Each thing the deliverable
  promised carries a grade or sits in the residuals as `UNSPECIFIED`, and a
  decision in neither is what gets invented at export time by whoever hits it first
- **Report `status`**: `DONE` (every promised decision made, every measurable
  claim measured, zero `UNSPECIFIED`) / `PARTIAL` / `BLOCKED` (say what was tried)
- **Every residual is `BLOCKED` / `OUT-OF-SCOPE` / `DEFERRED` / `UNSPECIFIED`**
  and appears in the handoff's `open`; a run holding `Write` also leaves a
  `#TODO(agent):` marker carrying that class in the document it produced
- **Never omit the sweep** — markers against `open`, promised decisions against
  graded ones: `swept, 0 markers; 6 decisions / 6 graded`. While either pair
  disagrees the status is not `DONE` (`_image/CONTRACT.md`)
<!-- /deliver:report -->

## Done when

The purpose is one sentence, the standard names something that exists, every
axis can be falsified, the exclusions are non-empty, and the brief says where
the picture lands and at what crops.
