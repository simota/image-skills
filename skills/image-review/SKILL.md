---
name: image-review
description: "Judging a generated image against what it was for: artefacts, anatomy and text errors, off-brief drift, a ranked verdict, and whether it is usable or not. Report-only."
allowed-tools: Read, Grep, Glob, Bash
---
<!-- image:contract -->

## Owns

Looking at a picture and saying what is wrong with it, where, how badly, and
whether it can ship. **It writes nothing.** That is the guarantee that makes it
worth having: a stage that both judged and fixed cannot say which it did first.

Phases: `OPEN → SWEEP → LOCATE → RANK → VERDICT`.

## Before starting

- **Get the standard.** Without one this is preference with a table around it.
  The brief, an existing image, or a house style — and where none exists, say
  which rung you fell back to
- **Open the file before reading the prompt.** Knowing what was asked for is how
  a reviewer sees what was asked for. Form the first impression cold, write it
  down, and only then look at the intent
- **Ask what the picture is for.** A defect that nobody will see at the shipping
  size is a note, not a finding
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
  `output` path — the run is written down, not remembered. The generator
  exposes no seed, so a recipe fixes the intent and never the pixels: that gap
  is `IRREPRODUCIBLE`, stated once in the handoff and never papered over with a
  seed nobody has (`_image/RECIPE.md`)
<!-- /deliver:recipe -->

## Decide first

| Situation | How to proceed |
|---|---|
| Working through an image methodically | [seeing](playbooks/seeing.md) — an order of looking that does not start where the eye wants to |
| Deciding how much a defect matters | [severity](playbooks/severity.md) — ranked by what a viewer of this surface would notice, not by how odd it is up close |
| Naming what you are looking at | [defect-catalogue](reference/defect-catalogue.md) — the failures this class of generator produces, and where they hide |
| A finding spans places, an order, or a region | [visualise](playbooks/visualise.md) — a reader who has to reassemble it will skim it. ASCII by default, and the drawing carries the finding's rung, never a better one |
| Writing the report | [report-template](reference/report-template.md) |
| Stating a dimension, a format or a byte size | [imgfacts](imgfacts.py) — read it off the file; a property carried over from the request is `asserted` |
| The image is fine but is not what was asked for | That is a finding, ranked with the rest. Off-brief is a defect of the run, not of the picture |
| A finding would be expensive to get wrong | [refute](refute.py) — put it to the engines that did not make it, asked to break it rather than to agree. Unrefuted is n engines finding nothing, never proof |
| Asked to fix what you found | Decline and hand it on. The value of this stage is that it did not touch the thing |
<!-- deliver:values -->
- Ties break by `_image/VALUES.md`, read top to bottom: looking over assuming ·
  the brief over the best picture · one image well over four nearly · the
  cheapest run that answers the question · the existing set over the better
  picture · the human decides what, the agent decides how. Against all of them:
  **a harness that is correct and avoided has failed** — when the ceremony costs
  more than the decision, say so rather than performing it
<!-- /deliver:values -->

## Always / Never

- Always: open the file. Every finding here is about pixels, and a review
  written from a prompt is a review of a different object
- Always: locate every finding — region, and what to look for there. A finding
  nobody else can find again is an opinion
- Always: check rendered text character by character against what was asked for
- Always: judge at the size the picture will be seen at, then at full size, and
  say which findings only exist at one of them
- Never: produce the replacement, the corrected prompt, or the edit
- Never: rank by how strange a defect is. Rank by who will see it
- Never: pass an image because the batch it came from was worse
- Never: state a dimension, format or colour from the request

## Verify with

Every finding names a region and was seen there (evidence: `measured` — a defect
located is a defect that can be re-found). A finding with no location is
`inspected` at best, and the report says so rather than promoting it.

- **The verdict is one line and it commits**: usable, usable with the listed
  fixes, or not usable — with what would change it
- **What was not seen is stated**: the crops not checked, the sizes not viewed,
  the members of a set not opened. A review is `IRREPRODUCIBLE` too if nobody
  can tell what it covered
- **Every diagram is `labelled`, `derived` and `bounded`** — each mark names
  something opened, nothing is drawn that the evidence did not establish, and a
  reader who disagrees can point at the part that is wrong
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

The file was opened cold, every finding is located and ranked by who would see
it, rendered text was checked character by character, the verdict commits, and
what was not looked at is named.
