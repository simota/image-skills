# image-skills

Six agent skills covering image work — deciding what a picture must say,
asking a generator for it, judging what comes back, and getting the file into a
project — plus the contracts they share and the budgets that keep the set from
growing into something nobody can route through.

**None of them generate pixels themselves.** The generation is one of two
installed tools — Codex's own `imagegen` skill and its built-in
`image_generation` tool, or the `generate_image` tool built into the `agy` CLI.
This set is the discipline around them: what to ask for, how many times, whether
anyone looked, and what has to be written down so the picture can be made again.

The two do not take the same argument. One takes a pixel canvas subject to four
constraints; the other takes an aspect ratio off a list of seven and no pixel
count at all, and writes JPEG. **Which one ran is the first thing a recipe
settles**, because half the fields beside an image mean something different
depending on the answer.

## The skills

| Skill | Owns | Produces |
|---|---|---|
| [`image-direction`](skills/image-direction/SKILL.md) | What the picture must say, and what it looks like saying it | A brief |
| [`image-prompt`](skills/image-prompt/SKILL.md) | The request the generator actually receives | A prompt record |
| [`image-generate`](skills/image-generate/SKILL.md) | Running it, what it cost, which candidate survives | Images and recipes |
| [`image-refine`](skills/image-refine/SKILL.md) | Changing a picture that already exists | Images and recipes |
| [`image-review`](skills/image-review/SKILL.md) | Whether the result is usable, and what is wrong with it | Nothing. Report-only |
| [`image-deliver`](skills/image-deliver/SKILL.md) | Getting the chosen file into the project | Files and their placement |

## The idea the set is built on

**Every image an output names carries the recipe that produced it.** `engine`,
`model`, `prompt` verbatim, `excluded`, `size` asked for and size on disk,
`inputs`, `output`. A picture is the one deliverable here that carries no
history inside itself: open the file six weeks later and nothing in it says
what was asked for or what it was made from, so the wording has to travel
beside it.

Neither generator exposes a seed. Running the same recipe again returns *another*
image from the same request, not the same image — so a recipe fixes the intent
and never the pixels. That gap is `IRREPRODUCIBLE`: stated once, never papered
over with a seed nobody has, and the reason the chosen file is the artifact
rather than something regenerated on demand
([`skills/_image/RECIPE.md`](skills/_image/RECIPE.md)).

## Evidence, for work whose plan and result look alike

An image *can* be run — it is a file, and a file can be opened. So the grade
here is about **whether anyone looked**. `measured` — the image opened and
viewed, its dimensions or bytes read, a defect located in a named region.
`inspected` — opened and reasoned over, with the reason nothing could be
measured. `asserted` — the claim alone, which never supports completion.

**The prompt is a request, never a description of what came back.** "It is 3:2
because I asked for 3:2" is `asserted`, and so is every count of fingers and
every word of rendered text taken from the wording rather than the pixels. This
is the failure the set is built around, and it is not hypothetical: asking the
default path for 1024×1024 produced a 1254×1254 file, because that path takes
no size argument at all.

**The unit is the decision, not the batch.** Four candidates and one export is
five files and a dozen decisions. Each promised decision carries a grade or
appears as `UNSPECIFIED` — which is what gets invented at export time by
whoever hits it first.

## How it is put together

A skill is loaded in three stages, and each costs something different. The
**listing** carries `name` and `description` only, for every enabled skill, on
every turn. **`SKILL.md`** is read in full once a skill is chosen. Anything it
points at is read only when the situation calls for it.

**Selection happens on the description alone.** Nothing else is in front of the
engine at that moment. So every word that selects a skill appears literally in
its description, and [`image-registry/capabilities.yaml`](image-registry/capabilities.yaml)
lists those words per skill. A rule checks the two agree.

**Boundaries live in one file.** That same registry carries `not:` — what a
skill does not do and where that work goes instead. Descriptions never name a
neighbour. If they did, adding a seventh skill would mean editing the other six,
and a description would spend its 200-character listing budget advertising a
competitor.

**Contracts are delivered, not referenced.** A rule kept in `skills/_image/` is
read on a minority of launches, so the operative part of each contract is copied
verbatim into every `SKILL.md` between `<!-- deliver:… -->` markers.
`image-registry/delivered/` holds the source, `make render` writes it back, and
a rule fails if any copy has drifted.

**Knowledge is split by whether it rots.** `playbooks/` holds judgement —
failure types, the order decisions go in, structures that stay true — and is
budgeted. `reference/` holds what goes stale — a model's size constraints, an
invocation, a taxonomy of edit modes — carries no line budget, and states its
purpose and the date anyone last checked it instead. A rule rejects a pinned
version, a date, or a model identifier inside a playbook: in this domain the
model name is the fastest-rotting string there is.

**Where a number follows from another number, a date is not enough.** A
`Verified:` line records that someone looked once; it cannot fail, so it cannot
catch a value edited into a wrong one later. `make figures` recomputes what the
reference layer states from the reference layer itself — every listed canvas
size put back through the four constraints the same page states, its ratio
reduced and its megapixel figure recomputed, every size listed as *rejected*
checked to still be rejected by the rule named against it, and every export rung
recomputed from its own base and factor. The twelve deliberate errors that prove
it can fail are not a claim in this file — they are `image-tools/test_figures.py`,
they run in `make check`, and five of them make the checks *vacuous* rather than
wrong: a row rewritten out of a computable shape, a table header renamed, a
constraint deleted from the prose it reads.

**Two tools, linked into the skills that can run them.**
[`imgfacts.py`](image-tools/imgfacts.py) reads what is actually in a file —
dimensions, format, bytes, alpha, whether a colour profile is declared, and
whether a canvas is legal, or an aspect offered, for the generator that will run
it. It is what makes `measured` cheap,
because a grade that costs effort gets skipped.
[`recipe.py`](image-tools/recipe.py) captures a generated file out of whichever
generator's directory holds the newest one and writes its recipe in the same
move, then checks that recipe against the file later. [`strip.py`](image-tools/strip.py) removes what
should not ship — Exif, XMP, generation parameters, comments, timestamps — while
keeping the colour profile, the alpha channel and any content credential the
project decided to carry.

None of the three needs an image library: they read and edit headers rather than
decoding pixels, so there is nothing to install beyond the PyYAML the harness
already requires, and nothing is ever re-encoded. A tool that needed a build step
before it could say how wide a file is would not get run.

`strip.py` names what stays rather than what goes, so a metadata block nobody
here has heard of is removed by default instead of shipped by default. It
refuses rather than guessing — a non-upright Exif orientation stops the run,
because dropping that flag without applying the rotation turns the picture
sideways somewhere downstream — and it re-reads its own output in memory,
before touching the disk, refusing if the dimensions, format, alpha or profile
moved. A run with neither `--out` nor `--in-place` writes nothing.

**One parser per format, shared.** `strip.py` reads JPEG through the same marker
scanner `imgfacts.py` uses. Two parsers of one format is two chances to disagree
about it, and a review found them doing exactly that on the fill bytes the
standard allows before a marker.

The tools directory is never linked whole — a skill holding `Bash` and all of it
could edit the harness it is part of. `linked_tools` in the registry names which
skills get which tool, and a rule checks each link is present exactly where the
skill's class grants a shell, so a missing one fails rather than passing as an
oversight.

**One declaration for the generators' numbers.** `generators` in the registry
holds both — the four canvas constraints for one, the seven aspects for the
other, each tagged with the `control` that separates them. `imgfacts.py` decides
legality from it, `image-prompt/reference/sizes.md` states both in prose for a
reader, and `make figures` checks the prose against the registry — so the tools
and the page cannot quietly disagree. Adding a third generator is a registry
edit; the tools resolve which is which by `control`, and assert rather than
picking whichever came first in the file.

**Budgets are enforced, not intended.**
[`image-registry/harness.yaml`](image-registry/harness.yaml) holds every
threshold. `image-tools/validate.py` decides them and CI fails on a violation.

**Generation is the only stage that spends money per attempt**, and it has no
natural stopping point, so the brief carries a `budget` field its sibling sets
do not have, `spent` travels in the handoff, and the one iteration loop carries
a hard cycle limit rather than a stopping condition alone.

## Names, and why none of them are generic

A skills directory is flat and shared with every other set installed on the
machine. A generic name placed there is a silent collision.

**One declaration.** `set: image` in `image-registry/harness.yaml` is the only
place the name is written. The prefix (`image-`), the shared directory
(`skills/_image/`), and the label every document carries all derive from it.

**Every directory this set owns carries the set name** — `image-*` or `_image`,
with only the platform's own directories exempt. Carrying the prefix is not what
makes something installable: a skill is a directory holding a `SKILL.md`, and
only those are linked.

**Everything a skill reads lives inside the skill**, reached through symlinks
named `_image` and `registry`. A skill is handed its own directory as the base
for relative paths, and those are normalised *lexically*, so `../_image/X.md`
does not travel back through the install symlink. A shell follows the link and
finds the file, which is what makes this fail quietly.

## Files

| File | What it fixes |
|---|---|
| [`skills/_image/CONTRACT.md`](skills/_image/CONTRACT.md) | Evidence grades, status, residual classes, the completion sweep |
| [`skills/_image/RECIPE.md`](skills/_image/RECIPE.md) | The seven fields every generated image carries, and what `IRREPRODUCIBLE` obliges |
| [`skills/_image/SIZING.md`](skills/_image/SIZING.md) | How much ceremony a request is worth; when a dialogue is mandatory; the brief |
| [`skills/_image/HANDOFF.md`](skills/_image/HANDOFF.md) | What passes between skills, and the checks the receiver runs |
| [`skills/_image/VALUES.md`](skills/_image/VALUES.md) | The order that decides when two goods conflict, and the escape hatch |
| [`skills/_image/ROUTING.md`](skills/_image/ROUTING.md) | Guidance. Read when the owner is unclear or the work spans several |

## Layout

```
image-skills/
├── README.md
├── Makefile
├── image-registry/             # budgets, boundaries, routes, delivered blocks
├── image-tools/                # imgfacts · recipe · strip · validate · figures · tests
└── skills/                     # everything the CLI reads
    ├── _image/                 # contracts in force on every run
    └── image-<facet>/          # a SKILL.md is what makes this a skill, and
        │                       # only skills are installed
        ├── SKILL.md            # Owns / Before starting / Decide first /
        │                       # Always·Never / Verify with / Done when
        ├── _image    -> ../_image        # short names: the parent scopes them
        ├── registry  -> ../../image-registry
        ├── imgfacts.py -> ../../image-tools/imgfacts.py   # declared per skill
        │                                 # in registry/harness.yaml linked_tools
        ├── playbooks/          # judgement. Budgeted, and must not rot
        └── reference/          # what goes stale. No line budget, dated instead
```

## Working on it

```sh
make check      # the rules, the figures, the tools, and proof each still fires
make render     # after editing anything in image-registry/delivered/
make hooks      # run the rules on every commit
```

Adding a rule means adding a deliberate violation to
`image-tools/test_validate.py`, and adding a figure check means adding one to
`image-tools/test_figures.py` — including one that makes the check vacuous
rather than wrong. A check only ever seen passing may be checking nothing.

The tools get the same treatment in `image-tools/test_tools.py`, and it is worth
saying what that has caught so far. Inverting the keyed-transparency branch in
`imgfacts.py` did not fail the suite, because no fixture had a `tRNS` chunk in
it. Dropping a standalone JPEG marker did not fail it, because the fixtures
checked what was removed and never that the rest survived byte for byte. And
widening `ASPECT_TOLERANCE` to 1.0 did not fail it, because the assertion read
the constant from the module it was testing — which passes for any value that
module picks. All three fixtures exist now. A test suite only ever seen passing
has the same problem a check does, and an assertion that borrows the
implementation's own number is the version of that which looks fine in review.

## Installing

```sh
make link                       # into ~/.claude/skills, ~/.codex/skills, ~/.gemini/…
make link CLAUDE_DIR=.claude/skills
```

Each `image-*` skill is linked individually, so a skills directory keeps
whatever else it already carries, and a name already taken by a real directory
is skipped rather than overwritten.

## The published overview

[`docs/index.html`](docs/index.html) is a generated page — every figure on it is
read off this repository, the way `make figures` recomputes what the reference
layer states. **Do not edit it by hand**: `tools/pages.py` in the `agent-toolkit`
repository writes it, `tools/pages.py --check` fails when it is behind, and
`.github/workflows/pages.yml` here only publishes what is committed.

## What this does not guarantee

- **Nothing here can make a generation reproducible.** Neither backing tool has
  a seed. Every claim about repeatability in this repository is about intent
- **`allowed-tools` is one CLI's mechanism.** Where a tool grant is not
  enforced, the `Never` lines are discipline and nothing more
- **No rule can check that a file was actually opened.** The contract says a
  claim about a picture rests on having looked; the validator cannot see whether
  anyone did. `imgfacts.py` makes the mechanical half cheap, and it is no
  evidence at all about the half that needs eyes: it reads headers, never pixels,
  so it cannot see a sixth finger, garbled lettering, or a shadow going the wrong
  way. That half is enforced by the refuting engine, or not at all
- **The fixtures do not model how a model chooses.** They catch a missing or
  duplicated signal. Passing them is not evidence that nothing will be misrouted
- **`Verified:` dates are not checked against anything.** A stale reference file
  with a fresh date passes. The date makes the staleness visible to a reader; it
  does not detect it
- **The backing skill is a moving target.** Its modes, its taxonomy and its size
  constraints are read off one installed copy on one machine, recorded in
  `reference/` with the date, and nothing re-checks them
