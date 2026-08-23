<!-- image:guidance -->
# Reading a reference without copying it

Someone hands over a picture and says "like this". That sentence hides a
question nobody has answered: *like this in which respect?* A reference is
never handed over whole — it is handed over for one or two properties, and the
rest comes along by accident unless it is named.

## Separate the four layers

Work down the list. Each is independently takeable, and each is independently
refusable.

| Layer | What it is | Safe to take? |
|---|---|---|
| Principle | Why it works — a single focal point, generous negative space, one light source | Yes. This is what a reference is for |
| Treatment | How it is executed — grain, palette temperature, depth of field, edge quality | Usually. Say which parts |
| Motif | Recurring concrete elements — the same object, the same gesture, the same crop | Sometimes. Two products sharing a motif read as one product |
| Identity | What makes it *theirs* — a mark, a signature palette, a named artist's hand, a recognisable set | No. Taking this is not inspiration |

The failure is treating the whole image as one thing. "Like this" then means
"all four", and identity is the layer with consequences.

## Write the answer down

The brief carries two lines per reference, and both are required:

```
took:  one light source from upper left; the empty upper third; muted, low-chroma palette
left:  the illustration style, the character, the brand's colour, the frame device
```

**`left` is the more useful line.** It is what a downstream stage checks itself
against when a generated result drifts back toward the reference. A reference
recorded with no `left` line is a reference nobody can tell you departed from.

## When there are several references

Say what each is for, by index, and expect them to conflict. Two references
handed over without roles produce an average of two looks, which resembles
neither and looks like a mistake rather than a decision.

```
ref 1 — composition and crop only
ref 2 — palette and light only
ref 3 — subject, for what the thing actually is
```

## The cases that are not reference reading

- **A competitor's image.** Take the principle, name it, and expect the
  question "does this look like theirs?" to be asked later by someone who has
  seen both
- **A named living artist.** Their name is a style handle to a generator and a
  person outside it. Do not put the name in a prompt; describe the properties
  you actually want instead, and say in the brief that this is what you did
- **A photograph of a real person.** Not a style reference. Stop
- **The product's own existing images.** Not a reference — the standard. The
  default is to match, and a departure is a decision that gets stated

## What this produces

Two lines per reference in the brief, and one sentence saying what the picture
would look like to someone who has never seen any of them. If that sentence
cannot be written, the reference was doing the work the direction should be.
