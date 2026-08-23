<!-- image:contract -->
# SIZING — how much ceremony the request is worth

Ceremony **above** what a request needs is what gets a harness worked around.
Ceremony **below** it is how a decision goes unmade. Both come from the same
move — choosing the tier for comfort — so the tier is read on first match.

## The three tiers

| Tier | All of these hold | What it costs |
|---|---|---|
| `T0` | One skill obviously owns it · reversible · one image or one value · the question fits in one sentence | Answer in a line. **No brief, no handoff** |
| `T1` | One skill owns it, but a `T0` condition fails | Settle the brief, then run. Handoff on return |
| `T2` | Two or more skills own parts of it, or the work spans phases | Route it: settle the brief once, run the chain, one report covers every stage |

`T0` drops the paperwork. It never drops the evidence grades or the recipe — a
one-line answer about a generated file still says what produced it and whether
anyone opened it.

**Finding mid-run that the tier was wrong means re-sizing and saying so.** A
`T0` export that has turned into a restyle is a `T1` that was mis-sized.

## When a dialogue is required first

This family fires the gate more often than most, because a picture request is
almost never uniquely determined by its words. Before executing, any of these
makes the dialogue mandatory:

- The shape of the deliverable is not uniquely determined — one image or a set,
  what it is for, where it appears
- What counts as achieved does not fit in one sentence
- The request carries a word with no achievement condition — "nicer", "cleaner",
  "more professional", "make it pop", "modern"
- The work would replace a picture a person already chose
- Doing it wrong would be expensive to undo — anything already published,
  anything under someone's name, anything depicting a real person or product

**Looking at what exists is not executing.** The current images, the brand
files, and the surface the picture lands on answer more questions than the
person can. Never open a dialogue over one reversible export.

## The brief the dialogue produces

Conclusions recorded as data, not as an understanding. Execution reads only
this.

```yaml
goal: "<one sentence describing the picture once it exists>"
delivers: "<a single artifact>"   # split the work if this goes plural
axes: [...]                       # what counts as achieved. Never one axis
excludes: [...]                   # what will not be decided. May not be empty
baseline: "<what exists now, opened and described>"
standard: "<what the result is judged against>"   # brief, an existing image, a house style
budget: "<how many paid generations this is worth>"
open_questions: []                # execution does not begin until empty
```

- **`standard` is this set's baseline for judgement.** Without one every
  candidate is arguable, and the iteration loop has no exit. Where none exists,
  say which rung you fell back to
- **`axes` may not collapse to one.** "Looks good" is a single oracle, and there
  is always a reading of it that can be declared satisfied. Subject, composition,
  technical cleanliness and fitness for the surface are four, and they trade
- **`budget` is a field this family has and its siblings do not**, because
  generation spends money per attempt and has no natural stopping point
- **`excludes` may not be empty.** Writing down what will not be decided is the
  only thing a downstream skill can check itself against
- **Execution does not begin while `open_questions` is non-empty.** Deferring an
  unknown to "I'll see what comes back" is how a batch becomes a fishing trip

## Constraints do not loosen mid-run

`axes`, `standard`, `baseline`, `budget`, and `excludes` are fixed at the start.
About to break one — stop and hand back. **An axis quietly dropped to make a
candidate defensible is the most expensive kind of false report**, because the
picture still looks finished.
