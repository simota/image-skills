- **Every image an output names carries its recipe.** `engine`, `model`,
  `prompt` verbatim, `excluded`, `size` asked for and size on disk, `inputs`,
  `output` path — the run is written down, not remembered, and `engine` says
  which of the two generators ran. Neither exposes a seed, so a recipe fixes the
  intent and never the pixels: that gap is `IRREPRODUCIBLE`, stated once in the
  handoff and never papered over with a seed nobody has (`_image/RECIPE.md`)
