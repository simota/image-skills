- **Retained generated candidates carry a recipe**: `engine`, reported `model`
  (or `unreported`), `prompt` verbatim, `excluded`, `size` requested/on disk,
  `inputs`, `output`. Capture the request at invocation; persist for candidates
  shown, kept or passed onward, not immediate discards. References and text-only
  outputs need no invented generation fields. `IRREPRODUCIBLE` limits exact pixel
  regeneration, not reuse or editing the source (`_image/RECIPE.md`)
