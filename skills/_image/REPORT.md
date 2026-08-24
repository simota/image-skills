<!-- image:contract -->
# REPORT — what a person reads

Binding on every `image-*` skill. The other axes decide what must be true; this
one decides what reaches the reader. A run that satisfies all of them and
returns forty lines has still failed: **a report that gets skimmed is a report
that did not happen**, and the one thing the reader wanted — is the picture
usable, and where is it — is the first thing a long report buries.

## Record and view are different objects

| Object | Holds | Read by |
|---|---|---|
| The handoff (`_image/HANDOFF.md`) and the recipe (`_image/RECIPE.md`) | Every field of the brief, every decision and its grade, the exact run that made the file | The next skill, and the person when they ask |
| The report | The answer, the line of evidence under it, what is unresolved | The person, now |

The report is a **view over** those records, never a second copy of them in
prose. A recipe restated line by line is the commonest way a one-line result
arrives as a paragraph.

## The moments a run speaks

Four, and no others. Each owes something different, and **what is right at one moment is
noise at the next.**

| Moment | What it owes | Ceiling |
|---|---|---|
| **Start** | What will be done and what is excluded, with the tier if it is not obvious | one line |
| **A question** | The one decision that is blocked, and the default taken if nobody answers | one question, one line |
| **Mid-run** | Nothing — unless the reader must act now: a divergence from what was agreed, a path found blocked, work that would grow the scope, a run that keeps missing the brief, or a budget about to be spent | one line each, or silence |
| **End** | The report below | the ceiling below |

**Progress is not information.** "generating candidates", "now upscaling",
"this one looks good" tell the reader nothing they can act on, and they cost
the same attention as the line that matters. A tool call is already visible;
narrating it a second time is the commonest way a run fills a screen while
saying nothing.

**A question is not a status update.** Ask when guessing wrong would be
expensive to undo, ask one thing, and say what happens if the answer never
comes.

## At the end — this order, every time

1. **The answer, one line.** The status, what was produced, and where it is. A
   reader who stops after this line has the result
2. **The evidence, one line.** The sweep (`_image/CONTRACT.md`), which already
   carries the counts: `swept, 0 markers; 9 decisions / 9 graded`
3. **What is unresolved** — one line per residual that needs a human decision.
   `BLOCKED` and `UNSPECIFIED` always. `DEFERRED` and `OUT-OF-SCOPE` are in the
   handoff and named here only if the reader would act on them today
4. **What is next** — one line, or nothing if the answer is nothing

A run with nothing unresolved reports lines 1 and 2 and stops.

## Ceiling

| Tier (`_image/SIZING.md`) | The whole report |
|---|---|
| `T0` | one line |
| `T1` | six lines |
| `T2` | ten lines, plus the files themselves |

**Over the ceiling means cutting content, not reformatting it.** A table, a
nested list, and a heading per candidate are the three ways a report grows
while appearing to have been tightened.

## The deliverable is not the report

The files are the deliverable and the recipe sits beside them. The report names
the path and says in one line what the picture is; it does not narrate the
prompt, the seed, or the candidates that lost. Those are in the recipe, which
is where a person goes to reproduce the run.

## Not bigger than it is

The requested scope is the deliverable. Neighbouring concerns, future
possibilities and general principles are not folded into the answer, and a
small ask does not come back as a survey. **Being thoughtful and diverging
are not the same thing** — thought goes deeper into the one thing asked,
never wider. Option lists are given when they were asked for, or when the
choice is the reader's to make.

**A real problem is the exception.** If the request would break something,
is unsafe, or rests on a false premise, say what is wrong, why, and the
options, at whatever length that takes. **Cut noise, never risk.**

## Never in a report

- A restatement of the brief, or of what the run was about to generate
- A closing summary of what was just said
- The prompt, the negative prompt, or the parameters — the recipe holds them
- Narration of process: how many candidates, which was tried first, which tool
- Praise for the output. Whether it is usable is a judgement with a grade
  behind it, not an adjective

## Asked for more

Bounding the default is not withholding. Every field lives in the handoff and
the recipe, and "why this one", "what did the others look like", "can it be
reproduced" are answered from them at whatever length the question deserves.
**The long form is available on request; it is just not the default.**
