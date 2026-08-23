<!-- image:contract -->
# CONTRACT — what counts as done

Binding on every `image-*` skill. A skill that reports completion without
satisfying this has reported a wish.

## Evidence grades

An image can be run — it is a file, and a file can be opened. So the grade here
is about **whether anyone looked**, not about whether a program executed.

| Grade | Means | Supports `DONE`? |
|---|---|---|
| `measured` | A property was read off the file — opened and viewed, dimensions or bytes or format read, a defect located in a named region | Yes |
| `inspected` | Opened and reasoned over, nothing read off it | Only where nothing can be measured, and the entry says why |
| `asserted` | The claim stands alone, or comes from the request rather than the result | Never |

**The prompt is a request, never a description of what came back.** "It is 3:2
because I asked for 3:2" is `asserted`, and so is every count of fingers, every
word of rendered text, and every colour read off the wording rather than the
pixels. This is the failure the set is built around: image work is the one
domain where the plan and the artifact look alike in a transcript and are
routinely different on disk. **A generation nobody opened is not a result — it
is a file path.**

## The unit of evidence is the decision

Not the batch. Four candidates and one export is five files and a dozen
decisions — which one, why, what size, what format, what it says to a reader
who cannot see it — and a file-level grade hides eleven of them. Every decision the deliverable promised either carries a grade or appears in the
residuals as `UNSPECIFIED`. **A decision in neither is invented at export time**,
by whoever hits it first, without knowing it was a decision.

## Status

| Status | Condition |
|---|---|
| `DONE` | Every promised decision made, every measurable claim measured, zero `UNSPECIFIED` |
| `PARTIAL` | Everything else that produced work — a single `UNSPECIFIED` lands here |
| `BLOCKED` | Could not proceed. Say what was tried and what stopped it |

A refusal from the generator is `BLOCKED`, reported as itself. Rewording until
a content filter stops objecting, without saying so, is the failure that looks
most like success.

## Residuals

Anything left behind is classified and recorded in the handoff's `open` list
with the place a reader would next look for it.

| Class | Means |
|---|---|
| `BLOCKED` | Wanted, attempted, prevented |
| `OUT-OF-SCOPE` | Found during the work, outside what was agreed. Named, not decided |
| `DEFERRED` | In scope, deliberately postponed, with the condition to resume named |
| `UNSPECIFIED` | Promised, and not decided |

**Who writes the marker depends on the tool grant.** A skill holding `Write`
puts a `#TODO(agent): <class> — <action>` line in the document it produced.
`image-review` holds no write grant: it records the entry in `open` and names
where the marker belongs. **A report-only skill never edits to satisfy this
rule** — here that would mean the judge had touched what it is judging.

## The completion sweep — never omitted

Before reporting, run both halves and state both results:

1. **Markers introduced by this run** — every one appears in `open` with a
   matching class
2. **Coverage** — the decisions the deliverable promised, against the decisions
   that carry a grade

Report it in one line: `swept, 1 marker / 1 in open; 9 decisions / 9 graded`.
**While either pair fails to match, the status is not `DONE`.**

## Boundary cases

- **A candidate not opened** is `asserted`, whatever the prompt said
- **One image of a set** evidences that image only. A family is measured member
  by member, or the claim is about one picture
- **A defect named without a location** is `inspected` at best. "There are
  artefacts" is not a finding; "the left hand, lower third" is
- **A file the generator wrote** evidences that a file exists, and nothing more
- **A recipe with no output path** cannot be checked later, and a claim resting
  on it is `asserted` (`_image/RECIPE.md`)
