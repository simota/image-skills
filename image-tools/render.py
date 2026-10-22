#!/usr/bin/env python3
"""Write the delivered blocks back into every SKILL.md.

A contract kept only in the shared directory is not read on most launches, so the operative
part is carried verbatim in each skill. That only stays true if changing one
line does not cost eight hand edits — this is that cost, paid once.

Idempotent: run it, commit the diff.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
H = yaml.safe_load((ROOT / "image-registry" / "harness.yaml").read_text(encoding="utf-8"))
PREFIX = H["prefix"]
SKILLS_ROOT = ROOT / H["skills_dir"] if H.get("skills_dir") else ROOT


# An ATX heading of level 1 or 2. A closing run of #s needs a space before it
# (CommonMark); "Name###" is the heading's text, not the heading closed.
HEADING = re.compile(r" {0,3}(#{1,2})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*")


def headings(text: str):
    """Every heading of level 1 or 2 outside a fence, as (start, end, level,
    title): where its line starts and where the next line does.

    Read line by line, as a renderer would: a heading quoted inside a fence is
    not one. Shared with the validator, so the two cannot disagree about where
    a section is."""
    pos, fence = 0, None
    for line in text.splitlines(keepends=True):
        bare = line.rstrip("\r\n")
        run = re.match(r" {0,3}(`{3,}|~{3,})", bare)
        if fence is not None:
            if run and run.group(1)[0] == fence[0] and len(run.group(1)) >= len(fence) \
                    and not bare[run.end():].strip():
                fence = None
        elif run and not (run.group(1)[0] == "`" and "`" in bare[run.end():]):
            fence = run.group(1)             # (a backtick in a backtick fence's
                                             # info string makes it plain text)
        else:
            m = HEADING.fullmatch(bare)
            if m:
                yield pos, pos + len(line), len(m.group(1)), m.group(2) or ""
        pos += len(line)


def section_span(text: str, section: str) -> tuple[int, int] | None:
    """Where the body of the H2 named `section` starts and ends, or None.

    An H3 with the same words is not the section, and the section ends at the
    next heading of level 1 or 2 rather than only at the next H2."""
    start = None
    for at, end, level, title in headings(text):
        if start is not None:
            return start, at
        if level == 2 and title == section:
            start = end
    return None if start is None else (start, len(text))


def render(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text
    for key, spec in H["delivered"].items():
        block = (ROOT / "image-registry" / "delivered" / f"{key}.md").read_text(
            encoding="utf-8").rstrip("\n")
        open_m, close_m = f"<!-- deliver:{key} -->", f"<!-- /deliver:{key} -->"
        payload = f"{open_m}\n{block}\n{close_m}"
        opens, closes = text.count(open_m), text.count(close_m)
        if (opens, closes) not in ((0, 0), (1, 1)) or (
                opens and text.index(open_m) > text.index(close_m)):
            # A lost marker, rendered past, duplicates the block now and deletes
            # whatever lies between the two opens on the next run.
            state = (f"unbalanced ({opens} open, {closes} close)" if opens != closes
                     else f"duplicated ({opens} of each)" if opens > 1
                     else "in the wrong order")
            raise SystemExit(f"{path}: deliver:{key} markers are {state}; "
                             "fix them by hand")
        if opens:
            head, rest = text.split(open_m, 1)
            _, tail = rest.split(close_m, 1)
            text = head + payload + tail
        else:
            span = section_span(text, spec["section"])
            if span is None:
                print(f"  {path.name}: no section {spec['section']!r}", file=sys.stderr)
                continue
            # append at the end of that section, before the next heading
            start, end = span
            head, body, tail = text[:start], text[start:end], text[end:]
            if not head.endswith("\n"):
                head += "\n"
            text = (head + body.rstrip("\n") + "\n" + payload + "\n"
                    + ("\n" + tail if tail else ""))
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> int:
    changed = [d.name for d in sorted(SKILLS_ROOT.glob(f"{PREFIX}*"))
               if (d / "SKILL.md").exists() and render(d / "SKILL.md")]
    print(f"rendered: {len(changed)} changed" + (f" ({', '.join(changed)})" if changed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
