<!-- image:deferred -->
Purpose: what to do about colour profiles and embedded metadata before a file ships.
Read when: colour looks different in place than in a viewer, or deciding what to strip.
Source: none — nothing outside this page can move what it states.
Verified: 2026-08-23 — the policy table below is what `strip.py` implements, and
it is re-checked by running `image-tools/test_tools.py`, which keeps and removes
each named block in PNG, JPEG and WebP. The browser and viewer behaviours below
have no automated check: they are stable properties of how profiles are handled,
nothing here re-runs them, and a project's own build may already do some of this.

# Colour and metadata

## The symptom this page exists for

The picture looks right in the file viewer and wrong on the page — usually
duller, sometimes shifted warm or cool. Almost always a colour-profile problem,
and almost always solved before the file ships rather than by adjusting the
picture.

## Profiles

An image file may carry a colour profile, may carry none, or may carry one that
disagrees with what the surface assumes.

- **Carries a profile the surface understands** → it is converted on display and
  looks right. This is the good case
- **Carries no profile** → the surface assumes its default, which on the web
  means sRGB. A wide-gamut image with no profile is displayed as though it were
  sRGB, and looks flat and desaturated
- **Carries a wide-gamut profile** → correct on a wide-gamut display,
  approximated elsewhere. Fine when deliberate, surprising when not

**The safe default for anything shipping to a browser is: convert to sRGB, and
keep the profile.** Converting without keeping is how the second case happens.

## Stripping metadata

`strip.py hero.png` reports what would go and what stays; `--out` or `--in-place`
writes it. It edits containers and never pixels — chunks and segments are copied
or dropped byte for byte, so nothing is re-encoded — and it re-reads its own
output **in memory**, before touching the disk, refusing if the dimensions,
format, alpha or profile moved. A run with neither `--out` nor `--in-place`
writes nothing at all, which is what makes it usable on a directory you only
have read access to.

Generated images arrive with metadata of varying usefulness. Strip by default,
with exceptions.

| Keep | Strip |
|---|---|
| The colour profile | Camera and lens fields |
| Orientation, or apply it and then strip it | GPS and location |
| Any provenance or content-credential block the project has decided to carry | Software and timestamps |
| Alpha channel | Thumbnails, previews, comments |

**Orientation is the one that bites.** Stripping an orientation flag without
first applying it rotates the picture ninety degrees somewhere downstream, on
some viewers and not others. `strip.py` refuses rather than guessing: an Exif
orientation that is not upright stops the run, because applying the rotation
would mean decoding the image, which is not this stage's job. Rotate the pixels
first, then pass `--orientation-is-applied`.

**Provenance blocks are a project decision, not this stage's.** If the project
has decided to carry a content credential or a generated-image marker, stripping
it is undoing a policy. Ask. `strip.py` keeps them unless told otherwise, and
`--drop-credentials` is how a person says so.

**Generation parameters are the reason to strip by default.** Several generators
write the prompt, the model and the settings into PNG text chunks or XMP; an
unstripped asset can publish the wording that made it, and sometimes a local
path. That information belongs in the recipe beside the file, which is
deliberate and version-controlled, not in the asset, which is public. The
generator this set is built around was measured and writes no such block — its
PNGs carry an `eXIf` holding colour space and pixel dimensions and nothing else
— and the default still removes it, because "this build wrote nothing sensitive
today" is not something a pipeline can rest on.

## Alpha

Check the alpha channel itself rather than trusting the look: many viewers
composite transparency onto white, so an opaque white background is
indistinguishable from a correct cutout until it lands on a coloured surface.

## Checks before shipping

`imgfacts.py` reports whether a profile is declared at all, and whether there is
an alpha channel, for every file at once. What it does not do is tell you the
profile is the *right* one — that is the check below, and it needs a person.

- The file's profile is what the surface assumes, read off the file
- Orientation was applied before it was stripped, and the picture is the right
  way up in something that ignores the flag
- Transparency, where it exists, verified in the alpha channel
- Nothing was stripped that the project decided to carry
