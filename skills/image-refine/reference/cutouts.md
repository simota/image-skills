<!-- image:deferred -->
Purpose: how a transparent-background asset is actually produced, since the default path has no transparency setting.
Read when: a cutout, sticker, sprite, or logo-on-anything asset is wanted.
Source: codex — the edit modes below are that CLI's, and move with its releases.
Verified: 2026-08-23 — the sequence, the helper path and the flags are quoted
from the installed backing skill. The helper was not run as part of this write-up,
so treat the flag behaviour as documented rather than observed; no automated check
re-reads it.

# Transparent backgrounds

**The default path has no transparency control.** Asking for "a transparent
background" in a prompt returns an opaque image of a checkerboard, or of white,
or of whatever the model thinks transparency looks like. This is the single most
common surprise in this domain.

## The sequence

1. **Generate on a flat chroma-key background.** Ask for one uniform colour, no
   shadows, no gradient, no floor plane, no reflection, crisp subject edges,
   generous padding
2. **Choose a key colour the subject cannot contain.** Default `#00ff00`; use
   `#ff00ff` for green subjects; avoid `#0000ff` for blue ones
3. **Copy the chosen output out of the generator's directory** before touching it
4. **Remove the key locally** with the installed helper:

```sh
python "${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/remove_chroma_key.py" \
  --input <source> --out <final.png> \
  --auto-key border --soft-matte \
  --transparent-threshold 12 --opaque-threshold 220 --despill
```

5. **Validate the result**: it has an alpha channel, the corners are
   transparent, the subject coverage is plausible, and there is no key-colour
   fringe. A thin fringe → retry once with `--edge-contract 1`. Visible
   stair-stepping on a matte, non-reflective subject → `--edge-feather 0.25`

## The prompt for step 1

```text
Create the requested subject on a perfectly flat solid #00ff00 chroma-key
background for background removal. The background must be one uniform color with
no shadows, gradients, texture, reflections, floor plane, or lighting variation.
Keep the subject fully separated from the background with crisp edges and
generous padding. Do not use #00ff00 anywhere in the subject. No cast shadow, no
contact shadow, no reflection, no watermark, and no text unless requested.
```

## When chroma keying will not do

Local key removal fails on subjects whose edges are not edges: hair, fur,
feathers, smoke, glass, liquid, translucent material, anything reflective, soft
contact shadows, and realistic product grounding. It also fails when no
practical key colour is safe against the subject's own palette.

For those the honest options are true model-native transparency on the fallback
CLI — a different model, an API key, and a decision the user makes — or a
different asset. **Ask before switching.** Silently changing model to satisfy a
transparency request is a substitution the user did not authorise, and the
backing skill says so explicitly.

## Validating alpha

Opening the file is not enough: many viewers composite transparency onto white
and a fully opaque white background looks identical to a correct cutout. Check
the alpha channel itself — corner pixels transparent, subject pixels opaque,
and a look along the edge for a coloured halo.
