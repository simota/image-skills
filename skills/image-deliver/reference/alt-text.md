<!-- image:deferred -->
Purpose: what the text replacing an image should say, decided by what the image is for.
Read when: writing alt text, or deciding whether an image needs any.
Verified: 2026-08-23 — no automated check. The categories below follow the
long-standing distinction between informative, decorative and functional images
in accessibility guidance; the wording advice is this repository's own.

# Alt text

Every image gets alt text or a stated reason it needs none. Leaving it to
whoever writes the markup means it is written by someone who never saw the
picture, or not written at all.

## What the image is for decides what the text says

| The image is | The text is |
|---|---|
| **Informative** — carries information the surrounding text does not | That information, in a sentence. Not a description of the picture |
| **Decorative** — carries nothing the text does not already say | Empty, and marked empty deliberately. An empty alt is a decision; a missing one is a bug |
| **Functional** — it is a control or a link | What it does, not what it shows. "Search", not "magnifying glass" |
| **Complex** — a chart, a diagram, an infographic | A short alt plus a longer description elsewhere. The alt says what kind of thing it is and where the description is |
| **Text as image** | The text, verbatim. All of it |

## Writing it

- **Say the point, not the contents.** A generated header image of a desk at
  dusk on a docs page is decorative — it is not "a wooden desk with a lamp",
  it is empty
- **Front-load.** Screen readers are often skimmed; the first few words carry it
- **No "image of", "photo of", "graphic showing".** The context already says it
  is an image
- **Length follows purpose.** One clause for most. A sentence where the
  information genuinely needs one. If it needs a paragraph, it is complex and
  the paragraph goes elsewhere
- **Punctuate it.** A full stop makes a reader pause where a sentence ends

## Generated images are decorative more often than people assume

An image made to fill a header, set a mood, or break up a page carries nothing a
reader needs. The honest alt is empty. Writing a loving description of a
decorative picture makes the page slower and worse to listen to, and it is the
most common alt-text mistake in this domain — not omission, over-description.

The test: **if the image were removed, would the reader have lost anything?**
No → empty alt. Yes → that thing is the alt text.

## What travels

The alt text, or the explicit decision that it is empty, travels with the file
and into whatever consumes it. "Alt: (decorative, deliberately empty)" in the
handoff is a completed decision. Silence is `UNSPECIFIED`.
