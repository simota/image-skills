<!-- image:guidance -->
# Structuring the request

A paragraph and a labelled spec containing the same words do not produce the
same picture, and only one of them can be diffed when the result changes.

## Write it as labelled lines

The backing skill reformats whatever it receives into a labelled spec anyway.
Sending a paragraph means that reformatting happens invisibly, by something
that is guessing which clause was the subject.

```text
Use case: <taxonomy slug>
Asset type: <where the asset will be used>
Primary request: <the main thing>
Input images: <Image 1: role; Image 2: role>
Scene/backdrop: <environment>
Subject: <main subject>
Style/medium: <photo / illustration / 3D / …>
Composition/framing: <wide / close / top-down; placement>
Lighting/mood: <lighting + mood>
Color palette: <palette notes>
Materials/textures: <surface details>
Text (verbatim): "<exact text>"
Constraints: <must keep / must avoid>
Avoid: <negative constraints>
```

Use the lines that carry a decision. An empty line is deleted, not filled with
something plausible — a `Color palette:` invented to avoid a blank is a
decision nobody made, and it will be defended in review as though it were one.

## The order inside a line

Wide to narrow: scene, then subject, then detail, then constraint. This matches
how the models weight a request and, more usefully, how a human reader checks
one against a brief.

## Length

Short and specific beats long and thorough. Every additional clause competes
with the others for attention, and past a point adding detail starts *removing*
control — the thing you cared about is now one of thirty things.

If a request is over about a dozen lines, something in it is decoration. Cut
the words with no visual consequence first.

## Text in the image

Rendered text is where this class of model fails most visibly and most often.

- Quote it verbatim, in the `Text (verbatim):` line, in quotes
- Spell hard or unusual words letter by letter
- Say where it sits and roughly how large
- Keep it short. Every extra word is another chance to garble
- Plan the check now: the result gets read character by character against this
  line, by a stage that opens the file

## Variants

One axis per variant, named. Four prompts differing on four axes tell you
nothing about any of them, and the pick becomes taste with no lesson in it.

```
v1  base
v2  base + light from behind        (axis: light)
v3  base + tighter crop             (axis: framing)
v4  base + illustration, not photo  (axis: medium)
```

## What travels forward

The exact text sent, verbatim, into the recipe's `prompt` field. Not the spec
you meant to send and not a tidied version — a paraphrase is a different
prompt, and nothing downstream can tell.
