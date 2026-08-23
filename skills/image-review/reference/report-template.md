<!-- image:deferred -->
Purpose: the shape of a review report, and what each part is for.
Read when: writing up a review.
Verified: 2026-08-23 — the fields are quoted from `_image/CONTRACT.md` and
`_image/HANDOFF.md`; a rule in `image-tools/validate.py` re-checks that this
skill's report block matches the delivered source, so the grading half cannot
drift. The layout below has no automated check.

# The report

A review writes nothing to the image and nothing to the project. This report is
its entire output, and its value is that a reader who did not do the review can
act on it without opening a conversation.

## The shape

```markdown
## Verdict

<usable | usable with the listed fixes | not usable> — <one sentence>

Judged against: <the standard, named>
Seen at: <shipping size, and full size>
Not seen: <crops not checked, members not opened, sizes not viewed>

## First impression (written before the brief was read)

<one line>

## Findings

| # | Severity | Where | What | Against |
|---|---|---|---|---|
| 1 | blocking | the sign, upper left | reads "PRODCUT" | brief: text verbatim |
| 2 | major | subject's left hand | six digits | — |
| 3 | minor | lower right, at 100% only | repeating grain pattern | — |

## Evidence

| Claim | Grade | How |
|---|---|---|
| finding 1 | measured | opened at full size; read character by character |
| finding 3 | measured | opened at 100%; not visible at 400px shipping size |
| "palette matches the set" | inspected | the four existing images opened and compared by eye; no value sampled |

## Open

- { what: "alt text is unwritten", class: UNSPECIFIED, marker: "docs/assets/README.md", written: false }

swept, 0 markers / 0 in open; 7 decisions / 7 graded
next: image-refine for findings 1–2; finding 3 is a note
```

## What each part is for

**The verdict first**, because it is the only line some readers will use. It
commits — "it depends" means the standard was never settled, and that is itself
the finding.

**Judged against**, or the report is preference. Name the brief, the existing
image, or the house style, and where none existed say which rung you fell back
to.

**Not seen** is the part reviewers skip and receivers need. A review that
covered one crop of one member of a set has said nothing about the others, and
silence reads as approval.

**The first impression** is data that cannot be recovered later. Once the brief
has been read, nobody in the room can un-know it.

**Every finding is located.** A row with no `Where` is not a finding; it is an
opinion, and it is ranked `note` with the reason it could not be located.

**Evidence rows are per claim**, not per image. A report with one evidence row
has graded the act of reviewing rather than the things it concluded.

## `written: false` is normal here

This skill holds no write grant, so every marker it records is unwritten. It
names where each belongs, and the first receiver holding `Write` places it.
Editing to satisfy the marker rule would break the one guarantee that makes a
report-only stage worth having.
