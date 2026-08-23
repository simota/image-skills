#!/usr/bin/env python3
"""Capture and check the recipe an image travels with.

`_image/RECIPE.md` is this set's signature mechanism: a generated picture carries
no history inside itself, so seven fields travel beside it. This writes them at
the moment of the run, when they are still facts, and checks them afterwards
against the file on disk.

    recipe.py capture --to assets/hero.png --prompt-file p.txt
    recipe.py check assets/hero.png
    recipe.py check --dir assets/

`capture` takes the newest file the generator left under $CODEX_HOME, copies it
where the project wants it, and writes the sidecar with the size read off the
file rather than the size the prompt asked for. Those two disagree more often
than anyone expects, which is the whole reason both are recorded.

It never overwrites: an existing destination is a sibling version decision for a
person to make (`image-deliver/playbooks/naming.md`), not something a tool does
while nobody is looking.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True
import imgfacts                                            # noqa: E402

H = yaml.safe_load((ROOT / "image-registry" / "harness.yaml").read_text(encoding="utf-8"))
GEN = H["generator"]
FIELDS = [f for f in H["vocabulary"]["recipe_fields"] if not f.isupper()]
SIDECAR = ".recipe.yaml"


def _block(dumper, data):
    """Keep the verbatim prompt readable. A prompt folded into a quoted scalar
    is still the right characters, and nobody will diff it."""
    style = "|" if "\n" in data.rstrip("\n") else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


yaml.add_representer(str, _block, Dumper=yaml.SafeDumper)

# The eighth case, and the honest one: this generator exposes no seed, so a
# recipe fixes intent and never pixels (`_image/RECIPE.md`).
NO_SEED = "IRREPRODUCIBLE — no seed; this file is the artifact"
UNASKED = "not specified; the built-in path takes no size argument"


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def newest_generated() -> Path | None:
    hits = sorted(codex_home().glob(GEN["output_glob"]),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    return hits[0] if hits else None


def sidecar_of(image: Path) -> Path:
    return image.with_name(image.name + SIDECAR)


# --- capture -----------------------------------------------------------------

def capture(a: argparse.Namespace) -> int:
    src = a.source or newest_generated()
    if src is None:
        print(f"nothing matches {GEN['output_glob']} under {codex_home()}; "
              "name the file with --from", file=sys.stderr)
        return 2
    if not src.exists():
        print(f"{src}: no such file", file=sys.stderr)
        return 2

    dest = a.to
    if dest.exists() and not a.replace:
        print(f"{dest} already exists. Write a sibling version instead, or pass "
              "--replace once a person has decided to retire the old one",
              file=sys.stderr)
        return 2

    facts = imgfacts.probe(src)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)

    inputs = []
    for spec in a.input or []:
        path, _, role = spec.partition(":")
        inputs.append({"path": path, "role": role or "unstated"})

    doc = {
        "engine": a.engine or GEN["invoke"],
        "model": a.model or "unreported",
        "prompt": a.prompt_file.read_text(encoding="utf-8") if a.prompt_file else a.prompt,
        "excluded": a.excluded or "none",
        "size": {"asked": a.asked or UNASKED, "on_disk": facts["size"]},
        "inputs": inputs,
        "output": {"generated": str(src), "placed": str(dest)},
        "note": NO_SEED,
    }
    side = sidecar_of(dest)
    doc["prompt"] = doc["prompt"].rstrip("\n") + "\n"
    side.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True,
                                   default_flow_style=False), encoding="utf-8")
    print(f"{dest}  {facts['size']}  {facts['bytes']:,} bytes")
    if doc["size"]["asked"] not in (UNASKED, facts["size"]):
        print(f"  asked for {doc['size']['asked']}, on disk {facts['size']} — "
              "both recorded")
    print(f"{side}  {len(FIELDS)} fields")
    return 0


# --- check -------------------------------------------------------------------

def check_one(image: Path) -> list[str]:
    side = sidecar_of(image)
    if not side.exists():
        return [f"{image}: no recipe. Record it as origin: unknown rather than "
                "reconstructing one — a remembered prompt is a plausible prompt"]
    try:
        doc = yaml.safe_load(side.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return [f"{side}: not readable as YAML ({e.__class__.__name__})"]

    problems = []
    for f in FIELDS:
        if f not in doc:
            problems.append(f"{side}: no {f}")
        elif doc[f] in (None, "", {}) and f != "inputs":
            problems.append(f"{side}: {f} is blank — a field nobody decided, "
                            "not one that does not apply")
    if isinstance(doc.get("prompt"), str) and len(doc["prompt"].strip()) < 20:
        problems.append(f"{side}: prompt is {len(doc['prompt'].strip())} characters. "
                        "The field is the text sent, verbatim, not a summary")
    placed = (doc.get("output") or {}).get("placed")
    if placed and Path(placed) != image:
        problems.append(f"{side}: output.placed is {placed}, beside {image}")

    try:
        facts = imgfacts.probe(image)
    except (imgfacts.Unreadable, OSError) as e:
        return problems + [f"{image}: {e}"]
    on_disk = (doc.get("size") or {}).get("on_disk")
    if on_disk != facts["size"]:
        problems.append(f"{side}: size.on_disk is {on_disk!r}, the file is "
                        f"{facts['size']}")
    return problems


def check(a: argparse.Namespace) -> int:
    targets = list(a.images)
    if a.dir:
        targets += [p for p in sorted(a.dir.rglob("*"))
                    if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}]
    if not targets:
        print("nothing to check", file=sys.stderr)
        return 2
    problems = [p for image in targets for p in check_one(image)]
    for p in problems:
        print(f"  {p}")
    print(f"{len(targets)} image(s), {len(problems)} problem(s)")
    return 1 if problems else 0


# --- show --------------------------------------------------------------------

def show(a: argparse.Namespace) -> int:
    for image in a.images:
        side = sidecar_of(image)
        print(f"=== {image}")
        print(side.read_text(encoding="utf-8") if side.exists()
              else "origin: unknown   # no recipe beside this file")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("capture", help="copy a generated file into the project "
                                       "and write its recipe")
    c.add_argument("--to", required=True, type=Path)
    c.add_argument("--from", dest="source", type=Path,
                   help="default: the newest file the generator left")
    c.add_argument("--prompt-file", type=Path, help="the text sent, verbatim")
    c.add_argument("--prompt", help="use --prompt-file where the prompt has newlines")
    c.add_argument("--excluded", help="what the request told it to leave out")
    c.add_argument("--asked", help="the size the prompt asked for, if it asked")
    c.add_argument("--model", help="as the run reported it")
    c.add_argument("--engine")
    c.add_argument("--input", action="append", metavar="PATH:ROLE")
    c.add_argument("--replace", action="store_true",
                   help="overwrite the destination; a person decides this")
    c.set_defaults(fn=capture)

    k = sub.add_parser("check", help="every field present, and the size matches "
                                     "the file")
    k.add_argument("images", nargs="*", type=Path)
    k.add_argument("--dir", type=Path, help="every image under here")
    k.set_defaults(fn=check)

    s = sub.add_parser("show", help="print the recipe beside an image")
    s.add_argument("images", nargs="+", type=Path)
    s.set_defaults(fn=show)

    a = p.parse_args(argv)
    if a.cmd == "capture" and not (a.prompt_file or a.prompt):
        p.error("capture needs --prompt-file or --prompt: the prompt is the asset")
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
