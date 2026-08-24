<!-- image:contract -->
# HANDOFF — passing work between image skills

Every `T1` and `T2` run returns one, whether the next reader is another skill, a
person, or a later session. It is the single place the facts live, and it is the
**record, not the report**: what a person reads is a bounded view over it
(`_image/REPORT.md`), never this object rendered field by field.

**`T0` is the exception** (`_image/SIZING.md`): a one-skill, reversible,
single-value change returns one line and no handoff. It still says where the
value came from and whether the file was opened.

## The object

```yaml
brief:                        # every field of the brief in _image/SIZING.md
  goal: "<one sentence describing the picture once it exists>"
  delivers: "<a single artifact>"
  axes: [...]                 # every one must hold
  excludes: [...]             # may not be empty
  baseline: "<what exists now, opened and described>"
  standard: "<what the result is judged against>"
  budget: "<paid generations this is worth>"
  open_questions: []          # must be empty; a non-empty one never travels
status: DONE                  # DONE | PARTIAL | BLOCKED  (_image/CONTRACT.md)
decided: "<what this stage settled, 1-3 lines>"
recipes:                      # one per image this handoff points at
  "assets/hero.png": { engine: ..., model: ..., prompt: ..., excluded: ...,
                       size: ..., inputs: ..., output: ... }
evidence:
  "<decision>": { level: measured, how: "<what was opened and what it showed>" }
open:
  - { what: "...", class: UNSPECIFIED, marker: "<file>:<section>", written: true }
spent: "3 generations of a budget of 6"
swept: "1 marker / 1 in open; 9 decisions / 9 graded"
next: "<the skill that should receive this, or none>"
```

- **`brief` travels whole and is not modifiable** — every field, not a subset.
  Rewriting it downstream is how scope creeps, and here it is invisible: the
  picture still looks like the thing that was asked for
- **`recipes` is what makes an image usable by anyone after you**
  (`_image/RECIPE.md`). A handoff naming a file and not its recipe has passed on
  a picture nobody can change. Each carries `IRREPRODUCIBLE` where it applies
- **The keys of `evidence` are decisions, not files** (`_image/CONTRACT.md`). A
  batch arriving with one entry is a batch whose decisions were not counted
- **`spent` travels or the budget means nothing.** The next stage inherits what
  is left, and a loop that has burned its budget hands back rather than starting
- **`standard` travels or the receiver cannot judge anything.** A review with no
  standard is preference, and the handoff says which it is
- **`open` carries a class and the class decides what happens.** `BLOCKED` and
  `UNSPECIFIED` stop the chain and go back to the human; `DEFERRED` and
  `OUT-OF-SCOPE` travel as record, so the receiver learns what was already
  decided against rather than rediscovering it
- **`written` says whether the marker is in the document yet.** A report-only
  skill sets it `false` and names where it belongs; the first receiver holding
  `Write` places it and flips the flag
- Pass the decisions, not the exploration. A rejected candidate belongs in the
  record only if a later stage may be asked to compare against it

## What the receiver checks before starting

1. Is a whole `brief` attached, with every field present? A pointer to one is
   not one, and a subset is a brief that lost a constraint in transit
2. Is `standard` set, and is it something this stage can actually judge against?
3. Does every image named in the work carry a recipe, and does `output` point at
   a file that is still there?
4. Does `open` hold a `BLOCKED` or `UNSPECIFIED`? Hand back to the human
5. Is every `evidence` level above `asserted`, and does every claim about a
   picture rest on the file having been opened rather than on the prompt?
6. Do `swept` and `evidence` agree, and does every marker counted appear in `open`?
7. Is any `open` entry `written: false`? If you hold `Write`, placing those
   markers is part of your run
8. Does `spent` leave budget for what this stage intends, and does the work fall
   outside the brief's `excludes`?

## Send-backs

A send-back **names the check that failed and the field it failed on**. Without
that, the same handoff returns unchanged and the round trip bought nothing — and
here it also bought another paid generation.

**After two round-trips on the same handoff, hand back to the human.** Being
rejected twice points at the brief or at how the work was divided, not at the
picture.
