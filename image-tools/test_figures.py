#!/usr/bin/env python3
"""Prove each check in figures_check.py fires.

`make figures` recomputes what the reference layer states. A checker only ever
seen printing "green" may be checking nothing — a regex that stopped matching,
a table renamed out from under it, a constraint deleted from the prose it reads.
Every case below breaks one page in a throwaway copy and fails if the checker
stays quiet.

Two kinds of case, and the second is the one that matters:

* **wrong** — a value edited into one that no longer follows. The obvious kind
* **vacuous** — the page edited so the checker matches nothing. These pass a
  naive checker silently, which is worse than failing, and they are why the
  checker collects every row of a table before judging any of them

Run: make figures-test
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIZES = "skills/image-prompt/reference/sizes.md"
RUNGS = "skills/image-deliver/reference/export-targets.md"
REG = "image-registry/harness.yaml"
IMGFACTS = "image-tools/imgfacts.py"

# (checker, kind, page, find, replace)
CASES: list[tuple[str, str, str, str, str]] = [
    ("check_sizes", "wrong", SIZES,
     "| `1536x1024` | 3:2 |", "| `1536x1000` | 3:2 |"),
    ("check_sizes", "wrong", SIZES,
     "| `2048x1152` | 16:9 |", "| `2048x1152` | 15:9 |"),
    ("check_sizes", "wrong", SIZES,
     "| `3840x2160` | 16:9 | 8.29 MP", "| `3840x2160` | 16:9 | 8.31 MP"),
    ("check_sizes", "wrong", SIZES,
     "| `1000x1000` | multiple of 16 |", "| `1024x1024` | multiple of 16 |"),
    # a row without its closing pipe is still a row; the table used to end
    # there, taking this row and every one after it out of the check
    ("check_sizes", "wrong", SIZES,
     "| `2048x2048` | 1:1 | 4.19 MP | square, print-ish |",
     "| `2048x2048` | 1:1 | 4.20 MP | square, print-ish"),
    ("check_sizes", "vacuous", SIZES,
     "1. Maximum edge is 3840px or less", "1. Keep the long edge sensible"),
    ("check_sizes", "vacuous", SIZES,
     "| `1024x1024` | 1:1 | 1.05 MP", "| about 1024 square | roughly 1:1 | about 1 MP"),
    ("check_sizes", "vacuous", SIZES,
     "| Size | Ratio | Megapixels | Use |", "| Canvas | Shape | Pixels | Use |"),
    # a megapixel figure that is not a number read as one, and crashed
    ("check_sizes", "vacuous", SIZES,
     "| `1024x1024` | 1:1 | 1.05 MP", "| `1024x1024` | 1:1 | 1.05. MP"),
    ("check_sizes", "vacuous", SIZES,
     "| Size | Breaks |", "| Size | Note |"),
    ("check_density", "wrong", RUNGS,
     "| `@1.5x` | 768x512 | 1.5 | 1152x768 |", "| `@1.5x` | 768x512 | 1.5 | 1152x769 |"),
    ("check_density", "wrong", RUNGS,
     "| `@1.5x` | 768x512 | 1.5 | 1152x768 |", "| `@1.5x` | 375x667 | 1.5 | 564x1001 |"),
    # 614.4 is not half a pixel: only an exact half may go either way
    ("check_density", "wrong", RUNGS,
     "| `@1.5x` | 768x512 | 1.5 | 1152x768 |", "| `@1.2x` | 768x512 | 1.2 | 922x615 |"),
    ("check_density", "wrong", RUNGS,
     "Source must be at least: 2304x1536", "Source must be at least: 1536x1024"),
    # the label says one density and the factor computes another; the emitted
    # size agrees with the factor, so only the label comparison can catch it
    ("check_density", "wrong", RUNGS,
     "| `@2x` | 768x512 | 2.0 | 1536x1024 |", "| `@2x` | 768x512 | 1.5 | 1152x768 |"),
    ("check_density", "vacuous", RUNGS,
     "Source must be at least: 2304x1536", "The source should be big enough."),
    # a second floor that disagrees with the first; only the first was read
    ("check_density", "wrong", RUNGS,
     "Source must be at least: 2304x1536",
     "Source must be at least: 2304x1536\n\nSource must be at least: 768x512"),
    ("check_density", "vacuous", RUNGS,
     "| `@1x` | 768x512 | 1.0 | 768x512 |", "| `@1x` | the CSS box | none | the same again |"),
    ("check_canvas", "wrong", REG, "    max_edge: 3840", "    max_edge: 4096"),
    # a second statement of a constraint that disagrees with the first; only
    # the first was ever read, so the page could say both
    ("check_sizes", "wrong", SIZES,
     "## Sizes that are rejected, and by which rule",
     "Note: Maximum edge is 4096px or less on newer installs.\n\n"
     "## Sizes that are rejected, and by which rule"),
    # a second table under the same header, with a row its own arithmetic
    # refutes; only the first table with a header was ever read
    ("check_sizes", "wrong", SIZES,
     "## Sizes that are rejected, and by which rule",
     "| Size | Ratio | Megapixels | Use |\n|---|---|---|---|\n"
     "| `1000x1000` | 1:1 | 1.00 MP | not a multiple of 16 |\n\n"
     "## Sizes that are rejected, and by which rule"),
    ("check_canvas", "wrong", REG, "    min_pixels: 655360", "    min_pixels: 65536"),
    ("check_canvas", "wrong", SIZES,
     "3. The long-to-short ratio is 3:1 or less", "3. The long-to-short ratio is 2:1 or less"),
    ("check_canvas", "vacuous", SIZES,
     "2. Both edges are multiples of 16",
     "2. Both edges land on the grid the model expects"),
    ("check_aspects", "wrong", REG,
     '"3:2", "3:4"', '"5:4", "3:4"'),
    ("check_aspects", "wrong", SIZES,
     "| `3:2` | landscape |", "| `6:4` | landscape |"),
    ("check_aspects", "vacuous", SIZES,
     "| Aspect | What it is for |", "| Ratio | What it is for |"),
    ("check_aspects", "vacuous", SIZES,
     "| `9:16` | tall, full-bleed on a phone |",
     "| tall as a phone | full-bleed |"),
    # the page and the constant drift apart from either side; the tool's own
    # tests bound the drift at 1%, so a change under that went unseen
    ("check_tolerance", "wrong", IMGFACTS,
     "ASPECT_TOLERANCE = 0.005", "ASPECT_TOLERANCE = 0.007"),
    ("check_tolerance", "wrong", SIZES,
     "the tolerance is 0.5%", "the tolerance is 2%"),
    ("check_tolerance", "vacuous", SIZES,
     "the tolerance is 0.5%", "the tolerance is small"),
    # the grid rule is named by its number, and the number is the page's
    ("check_sizes", "wrong", SIZES,
     "| `1000x1000` | multiple of 16 |", "| `1000x1000` | multiple of 8 |"),
]


# Valid tables a check must still read: GFM makes the outer pipes optional, so
# a row or a delimiter without its closing one is ordinary writing. A list of
# edits is one consistent change made in several places at once.
QUIET: list = [
    (SIZES, "| `2048x2048` | 1:1 | 4.19 MP | square, print-ish |",
     "| `2048x2048` | 1:1 | 4.19 MP | square, print-ish"),
    (SIZES, "| Size | Breaks |\n|---|---|", "| Size | Breaks |\n|---|---"),
    (RUNGS, "| `@1.5x` | 768x512 | 1.5 | 1152x768 |", "| `@1.5x` | 768x512 | 1.5 | 1152x768"),
    # half a pixel, rounded up on one edge and down on the other: the page
    # names no rule, and round() accepted only the even neighbour
    (RUNGS, "| `@1.5x` | 768x512 | 1.5 | 1152x768 |", "| `@1.5x` | 375x667 | 1.5 | 563x1000 |"),
    # the grid moved everywhere at once: the rejected row names the new number,
    # which a rule name written into the checker refused
    [(REG, "    edge_multiple: 16", "    edge_multiple: 8"),
     (SIZES, "2. Both edges are multiples of 16", "2. Both edges are multiples of 8"),
     (SIZES, "| `1000x1000` | multiple of 16 |", "| `1004x1004` | multiple of 8 |")],
]


def run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(root / "image-tools" / "figures_check.py")],
                          capture_output=True, text=True)


def main() -> int:
    baseline = run(ROOT)
    if baseline.returncode:
        print("the working tree is already failing; fix that first:\n"
              + baseline.stdout + baseline.stderr)
        return 1

    silent: list[str] = []
    for i, (checker, kind, page, old, new) in enumerate(CASES, 1):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "repo"
            shutil.copytree(ROOT, copy, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            f = copy / page
            text = f.read_text(encoding="utf-8")
            if old not in text:
                print(f"  case {i} ({checker}, {kind}): fixture text no longer in "
                      f"{page}: {old[:50]!r}")
                silent.append(f"{i}:{checker}/{kind}")
                continue
            f.write_text(text.replace(old, new, 1), encoding="utf-8")
            r = run(copy)
            # The named checker must be the one that fired: a neighbour
            # catching the same edit proves nothing about this checker.
            if not r.returncode or f"[{checker}]" not in r.stdout:
                silent.append(f"{i}:{checker}/{kind}")
                print(f"  case {i} ({checker}, {kind}) did not fire\n{r.stdout}{r.stderr}")

    for i, entry in enumerate(QUIET, 1):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "repo"
            shutil.copytree(ROOT, copy, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            gone = False
            for page, old, new in entry if isinstance(entry, list) else [entry]:
                f = copy / page
                text = f.read_text(encoding="utf-8")
                gone = gone or old not in text
                f.write_text(text.replace(old, new, 1), encoding="utf-8")
            if gone:
                silent.append(f"quiet {i}: fixture text gone")
                continue
            r = run(copy)
            if r.returncode:
                silent.append(f"quiet {i}")
                print(f"  quiet case {i} fired\n{r.stdout}{r.stderr}")

    kinds = {k for _, k, *_ in CASES}
    print(f"{len(CASES)} cases exercised ({', '.join(sorted(kinds))}), "
          f"{len(silent)} silent")
    if silent:
        print("silent: " + ", ".join(silent))
        return 1

    # Counting cases says nothing about the checkers that exist. A checker added
    # without a case would otherwise leave this printing "every check fires".
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.dont_write_bytecode = True
    import figures_check                                   # noqa: E402
    declared = {n for n in vars(figures_check) if n.startswith("check_")}
    covered = {c for c, *_ in CASES}
    missing = sorted(declared - covered)
    if missing:
        print("no deliberate error is injected for: " + ", ".join(missing))
        return 1
    # A checker with only `wrong` cases is a checker nothing has tried to make
    # vacuous, and vacuity is the failure mode this file exists for.
    for c in sorted(declared):
        if not any(k == "vacuous" for ch, k, *_ in CASES if ch == c):
            print(f"{c} has no vacuity case")
            return 1
    print(f"every check fires ({len(declared)} checks, {len(CASES)} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
