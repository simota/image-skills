<!-- image:guidance -->
# How many to run

Generation is the only stage in this family that costs money per attempt and
the only one with no natural stopping point. Both facts push the same way:
decide the count before the first run, from the question, not from the results.

## The count follows the question

| The question is | Run | Because |
|---|---|---|
| "does this prompt work at all" | 1 | A second copy of an unanswered question answers nothing |
| "which of these directions" | 1 per direction, one axis apart | The comparison is the point; anything else varying ruins it |
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

Square is typically fastest and smallest. While the prompt is still moving, run
square drafts; pay for the final aspect and the final resolution once it has
stopped moving. A four-way direction test at full resolution is three quarters
wasted by definition.

## Variants differ on one axis

One axis per variant, named in the record. Four variants differing on four
things produce a winner nobody can learn from, and the next request starts from
scratch.

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

Every run gets a recipe, including the ones discarded — the discarded ones are
how a later reader knows what was already tried. What may be dropped is the
image files of rejected candidates, not the record that they existed.
