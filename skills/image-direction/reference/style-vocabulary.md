<!-- image:deferred -->
Purpose: which words in a direction survive into a prompt and move an image, and which are decoration.
Read when: writing the look half of a brief, or wondering why a described mood did not arrive.
Verified: 2026-08-23 — the categories are re-checked by running a prompt with and
without each word class and comparing; the specific claims below come from the
backing skill's own prompting guidance and from generations run against it.

# Words that move an image, and words that do not

A direction is read by a person and then compressed into a request by a
different stage. Words that carry no visual consequence survive the compression
looking important and arrive meaning nothing.

## The three classes

**Physical** — describes something a camera or a hand could have done. These
survive intact and are the reason a picture looks the way it does.

> low sun from the left · shallow depth of field · matte paper texture ·
> hard shadow · shot from below · single light source · visible brush marks ·
> heavy grain · cool grey · desaturated · centred · cropped tight

**Consequential** — an abstraction that a physical description would satisfy.
Usable, but only as a heading over the physical line that implements it.

> calm · industrial · editorial · handmade · clinical · nostalgic

**Empty** — a quality claim with no visual consequence at all. It flatters the
brief and does nothing to the picture.

> beautiful · high quality · professional · stunning · masterpiece · 8k ·
> award-winning · modern · clean · elegant

## The rule

**Every consequential word is followed by the physical words that achieve it.**
A brief that says "calm" and stops has left the achievement to the generator,
and the generator's idea of calm is the average of its training data.

```
calm  →  one light source, low contrast, nothing in motion, wide empty
         foreground, cool desaturated palette
```

**Every empty word is deleted.** Not softened — deleted. "High quality" costs
prompt budget, adds nothing, and makes the request read as though its author
had nothing specific to ask for.

## Where this bites

- **"Minimal"** is the most common empty-consequential confusion. It can mean
  few objects, a restrained palette, a lot of negative space, or a flat
  illustration style. Pick the one you meant and write it physically
- **"Realistic"** is a medium, not a quality. Say photograph, and then say what
  kind of photograph, because the word alone selects a stock-photo average
- **Style names of living artists** are physical in effect and a problem in
  kind. Describe the properties instead, and say in the brief that this was
  done deliberately
- **Camera and lens language** is physical and works, but it commits: naming a
  focal length fixes the perspective, and a brief that names one and then asks
  for a wide establishing shot is asking for two things

## Checking a look description

Read each word and ask: *what would be different in the file if I removed it?*
A word with no answer is decoration. A word whose answer is "it would be worse"
is empty. A word whose answer names something visible is the only kind worth
sending.
