<!-- image:guidance -->
# How many to run

Generation and generative refinement share the paid-attempt budget. Decide
the count before a run, from the question, not from the results. Failed/refused
attempts remain in the record; unknown billing is not zero cost.

## The count follows the question

| The question is | Run | Because |
|---|---|---|
| "does this prompt work at all" | 1 | A second copy of an unanswered question answers nothing |
| "which of these directions" | 1 per retained direction hypothesis | Isolate an axis for causal comparison; a production hypothesis may bundle related axes |
| "is this reliably good, or was that luck" | 3 of the same prompt | Variance is the thing being measured |
| "we need a matching set of four" | 1 per member, same prompt skeleton | Consistency comes from the skeleton, not from volume |
| "none of these are right" | 0 | Two failed batches on one prompt is a prompt problem or a brief problem, and a third batch will not say which |

## The rule that saves the most money

**Before a batch, write the sentence: "this run will tell us ___."** If the
blank cannot be filled, the run is a wish. The most common unfillable case is
the second batch after a disappointing first — the honest sentence there is
"this will tell us whether we get lucky", and that is a decision to gamble,
which is fine as long as it is named as one.

## Cheap first

Use a cheaper draft only when the installed controls and cost model actually
make it cheaper and its composition is informative for the final surface. A
square draft is not automatically cheaper; an extra draft with no cost or
learning advantage is an extra paid call. Do not invent prices or size controls.

## Variants follow the question

A controlled comparison isolates one axis. Production search can bundle related
axes under a stated target and the same budget. Name what changed and why;
selection can find a usable candidate without proving which change caused it.

## Stopping

Stop when any of these is true, and say which one:

- The brief's axes all hold on one candidate. Stop even if a nicer one might exist
- Two batches on one prompt have failed the same way. The problem is upstream
- The budget is spent. Report `PARTIAL` with what was learned; do not quietly
  extend it
- The next run has no question

**"None of them are quite right" is not a reason to run again.** It is a reason
to say what "right" would look like, which is a brief question, not a batch.

## Recording a batch

Capture the submitted request at invocation. Persist recipes for retained
candidates, including all candidates passed to later comparison; immediate
discards need none. Keep compact attempt/outcome/spend records for discarded,
failed and refused runs. A file that does not exist cannot have an image recipe.
