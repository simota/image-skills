#!/usr/bin/env python3
"""Recompute the numbers the reference layer states, from the reference layer.

A `Verified:` date says a human looked once. It cannot fail. These checks parse
the tables out of the pages themselves and recompute them, so a value edited
into a wrong one breaks the build instead of ageing quietly.

    make figures

Two things are checked, and both are arithmetic the same page already states:

* `image-prompt/reference/sizes.md` — every size listed as legal is put back
  through the four constraints that page states, and its stated ratio and
  megapixel figure are recomputed. Every size listed as rejected must still be
  rejected, by the rule named against it and not merely by some other rule.
* `image-deliver/reference/export-targets.md` — every density rung is recomputed
  from its own stated base and factor, and the stated source floor is checked
  against the largest rung.
* the same four constraints, as prose on that page against `generator.canvas` in
  the registry. The page is written for a reader and the registry is what
  `imgfacts.py` decides legality from; one declaration means the tool and the
  page cannot quietly disagree.

Add a checker here whenever a reference page states a number that follows from
another number on the same page.
"""
import math
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
failures: list[str] = []


def fail(where: str, msg: str) -> None:
    failures.append(f"  {where}: {msg}")


# --- canvas sizes ----------------------------------------------------------

# Quoted from the page, and re-read from it rather than hard-coded here: a
# constraint copied into this file is a second definition that drifts.
CONSTRAINT_RE = {
    "max edge": re.compile(r"Maximum edge is (\d+)px or less"),
    "multiple of 16": re.compile(r"Both edges are multiples of (\d+)"),
    "ratio": re.compile(r"long-to-short ratio is (\d+):1 or less"),
    "total pixels": re.compile(
        r"Total pixels are between ([\d,]+) and ([\d,]+) inclusive"),
}

LEGAL_ROW = re.compile(
    r"^\|\s*`(\d+)x(\d+)`\s*\|\s*(\d+):(\d+)\s*\|\s*([0-9.]+) MP\s*\|")
REJECT_ROW = re.compile(r"^\|\s*`(\d+)x(\d+)`\s*\|\s*([a-z0-9 ]+?)\s*\|\s*$")

LEGAL_HEAD = re.compile(r"^\|\s*Size\s*\|\s*Ratio\s*\|\s*Megapixels\s*\|")
REJECT_HEAD = re.compile(r"^\|\s*Size\s*\|\s*Breaks\s*\|")
RUNG_HEAD = re.compile(r"^\|\s*Rung\s*\|\s*Base\s*\|\s*Factor\s*\|\s*Emitted\s*\|")
SEP = re.compile(r"^\|[\s:|-]+\|$")


def table_rows(text: str, head: re.Pattern) -> list[tuple[int, str]]:
    """Every data row of the named table, matching the row pattern or not.

    Filtering to rows that already parse would enforce each page's arithmetic
    only on the rows that already follow it. A row rewritten to say
    "about 1536 wide, roughly 3:2" would drop out of the check and the build
    would stay green, so the row is collected first and judged second.
    """
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if head.match(l.strip())), None)
    if start is None:
        return []
    out = []
    for i in range(start + 1, len(lines)):
        s = lines[i].strip()
        if SEP.match(s):
            continue
        if not (s.startswith("|") and s.endswith("|")):
            break
        out.append((i + 1, s))
    return out


def _limits(text: str) -> dict:
    out = {}
    for name, rx in CONSTRAINT_RE.items():
        m = rx.search(text)
        if not m:
            fail("sizes.md", f"the {name!r} constraint is no longer stated in a "
                             "form this checker can read — it is checking nothing")
            return {}
        out[name] = [int(g.replace(",", "")) for g in m.groups()]
    return out


def _breaks(w: int, h: int, lim: dict) -> set[str]:
    broken = set()
    if max(w, h) > lim["max edge"][0]:
        broken.add("max edge")
    if w % lim["multiple of 16"][0] or h % lim["multiple of 16"][0]:
        broken.add("multiple of 16")
    if max(w, h) / min(w, h) > lim["ratio"][0]:
        broken.add("ratio")
    lo, hi = lim["total pixels"]
    if not (lo <= w * h <= hi):
        broken.add("total pixels")
    return broken


def check_sizes() -> int:
    """Legal rows must satisfy every constraint and state the right ratio and
    megapixels; rejected rows must break exactly the rule named against them."""
    page = SKILLS / "image-prompt/reference/sizes.md"
    text = page.read_text()
    lim = _limits(text)
    if not lim:
        return 0

    legal_rows = table_rows(text, LEGAL_HEAD)
    reject_rows = table_rows(text, REJECT_HEAD)
    if not legal_rows:
        fail("sizes.md", "no legal-size table found — the checker has stopped "
                         "checking anything")
        return 0
    if not reject_rows:
        fail("sizes.md", "no rejected-size table found; without one the "
                         "constraints are never shown to reject anything")

    legal, rejected = [], []
    for i, line in legal_rows:
        m = LEGAL_ROW.match(line)
        if m:
            legal.append((i, m))
        else:
            fail(f"sizes.md:{i}", "row does not state a `WxH` size, a ratio and "
                                  f"a megapixel figure, so nothing about it can "
                                  f"be recomputed — {line[:60]}")
    for i, line in reject_rows:
        m = REJECT_ROW.match(line)
        if m:
            rejected.append((i, m))
        else:
            fail(f"sizes.md:{i}", "row does not state a `WxH` size and the rule "
                                  f"it breaks — {line[:60]}")

    for i, m in legal:
        w, h, ra, rb, mp = (int(m.group(1)), int(m.group(2)), int(m.group(3)),
                            int(m.group(4)), float(m.group(5)))
        broken = _breaks(w, h, lim)
        if broken:
            fail(f"sizes.md:{i}", f"{w}x{h} is listed as legal but breaks "
                                  f"{sorted(broken)}")
        g = math.gcd(w, h)
        if (w // g, h // g) != (ra, rb):
            fail(f"sizes.md:{i}",
                 f"{w}x{h} states {ra}:{rb}, reduces to {w // g}:{h // g}")
        actual = w * h / 1_000_000
        if round(actual, 2) != round(mp, 2):
            fail(f"sizes.md:{i}",
                 f"{w}x{h} states {mp} MP, computes {actual:.4f} MP")

    for i, m in rejected:
        w, h, named = int(m.group(1)), int(m.group(2)), m.group(3).strip()
        if named not in CONSTRAINT_RE:
            fail(f"sizes.md:{i}", f"breaks {named!r}, which is not one of the "
                                  f"four constraints {sorted(CONSTRAINT_RE)}")
            continue
        broken = _breaks(w, h, lim)
        if named not in broken:
            fail(f"sizes.md:{i}", f"{w}x{h} is listed as breaking {named!r} and "
                                  f"does not; it breaks {sorted(broken) or 'nothing'}")
    return len(legal) + len(rejected)


# --- density rungs ---------------------------------------------------------

RUNG_ROW = re.compile(
    r"^\|\s*`@[0-9.]+x`\s*\|\s*(\d+)x(\d+)\s*\|\s*([0-9.]+)\s*\|\s*(\d+)x(\d+)\s*\|")
FLOOR = re.compile(r"Source must be at least:\s*(\d+)x(\d+)")


def check_density() -> int:
    """Every rung is its own stated base times its own stated factor, and the
    stated source floor is the largest rung."""
    page = SKILLS / "image-deliver/reference/export-targets.md"
    text = page.read_text()
    raw = table_rows(text, RUNG_HEAD)
    if not raw:
        fail("export-targets.md", "no density-rung table found — the checker has "
                                  "stopped checking anything")
        return 0
    rows = []
    for i, line in raw:
        m = RUNG_ROW.match(line)
        if m:
            rows.append((i, m))
        else:
            fail(f"export-targets.md:{i}",
                 "row does not state a rung, a base, a factor and an emitted "
                 f"size, so nothing about it can be recomputed — {line[:60]}")
    widest = (0, 0)
    for i, m in rows:
        bw, bh, f, ew, eh = (int(m.group(1)), int(m.group(2)), float(m.group(3)),
                             int(m.group(4)), int(m.group(5)))
        want = (round(bw * f), round(bh * f))
        if (ew, eh) != want:
            fail(f"export-targets.md:{i}",
                 f"{bw}x{bh} x {f} is {want[0]}x{want[1]}, stated as {ew}x{eh}")
        if ew * eh > widest[0] * widest[1]:
            widest = (ew, eh)

    m = FLOOR.search(text)
    if not m:
        fail("export-targets.md", "no `Source must be at least: WxH` line; the "
                                  "floor the rungs imply is not stated")
    else:
        stated = (int(m.group(1)), int(m.group(2)))
        if stated != widest:
            fail("export-targets.md",
                 f"source floor is stated as {stated[0]}x{stated[1]}; the "
                 f"largest rung is {widest[0]}x{widest[1]}")
    return len(rows)


def check_canvas() -> int:
    """The four numbers the page states in prose are the four in the registry.

    `imgfacts.py` reads the registry; a reader reads the page. Without this the
    two are separate definitions, and the tool would keep answering correctly
    while the page told somebody otherwise.
    """
    page = SKILLS / "image-prompt/reference/sizes.md"
    lim = _limits(page.read_text())
    if not lim:
        return 0
    canvas = yaml.safe_load(
        (ROOT / "image-registry" / "harness.yaml").read_text())["generator"]["canvas"]
    stated = {"max edge": [canvas["max_edge"]],
              "multiple of 16": [canvas["edge_multiple"]],
              "ratio": [canvas["max_ratio"]],
              "total pixels": [canvas["min_pixels"], canvas["max_pixels"]]}
    for name, want in stated.items():
        if lim[name] != want:
            fail("sizes.md", f"states {name} as {lim[name]}; the registry's "
                             f"generator.canvas says {want}")
    return len(stated)


def main() -> int:
    sizes = check_sizes()
    rungs = check_density()
    canvas = check_canvas()
    if failures:
        print(f"{len(failures)} mismatch(es):")
        print("\n".join(failures))
        return 1
    print(f"figures green - {sizes} canvas sizes rechecked against their own "
          f"constraints, {canvas} of those constraints matched to the registry, "
          f"{rungs} density rungs recomputed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
