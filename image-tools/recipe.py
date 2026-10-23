#!/usr/bin/env python3
"""Capture and check the recipe an image travels with.

`_image/RECIPE.md` is this set's signature mechanism: a generated picture carries
no history inside itself, so seven fields travel beside it. This writes them at
the moment of the run, when they are still facts, and checks them afterwards
against the file on disk.

    recipe.py capture --to assets/hero.png --prompt-file p.txt
    recipe.py check assets/hero.png
    recipe.py check --dir assets/

`capture` takes the newest file a generator left in its own output directory,
copies it where the project wants it, and writes the sidecar with the size read
off the file rather than the size the prompt asked for. Those two disagree more
often than anyone expects, which is the whole reason both are recorded.

Which generator produced it is not guessed from the environment: with no
`--generator` and no `--from`, every declared generator's output directory is
searched and the newest file across all of them wins, so the answer comes from a
timestamp rather than from an assumption about which CLI is running. A file
named with `--from` is attributed to the generator whose output directory holds
it; one held by neither needs `--generator`, because recording the default would
put a command nobody ran into `engine`.

It never overwrites: an existing destination is a sibling version decision for a
person to make (`image-deliver/playbooks/naming.md`), not something a tool does
while nobody is looking.
"""
from __future__ import annotations

import argparse
import fcntl
import os
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True
import imgfacts                                            # noqa: E402

H = yaml.safe_load((ROOT / "image-registry" / "harness.yaml").read_text(encoding="utf-8"))
GENERATORS = {n: g for n, g in H["generators"].items() if isinstance(g, dict)}
DEFAULT_GENERATOR = H["generators"]["default"]
FIELDS = [f for f in H["vocabulary"]["recipe_fields"] if not f.isupper()]
SIDECAR = ".recipe.yaml"


# Characters YAML reads as line breaks, and folds or normalises unless they are
# escaped. A prompt holding one is double-quoted, the one style that escapes them.
_YAML_BREAKS = ("\r", "\x85", "\u2028", "\u2029")


def _block(dumper, data):
    """Keep the verbatim prompt readable. A prompt folded into a quoted scalar
    is still the right characters, and nobody will diff it."""
    if any(c in data for c in _YAML_BREAKS):
        style = '"'
    else:
        style = "|" if "\n" in data.rstrip("\n") else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


yaml.add_representer(str, _block, Dumper=yaml.SafeDumper)

# Capture does not establish deterministic regeneration or current seed support.
# The note limits that claim; it does not prevent reusing this exact source file.
NO_SEED = "IRREPRODUCIBLE — exact regeneration not established; this file is the artifact"

# What `size.asked` says when nothing asked. Kept per control surface, because
# "no size argument" and "an aspect, and no pixel count at all" are different
# facts about the run and a reader six weeks later needs the right one.
UNASKED = {
    "canvas": "not specified; the built-in path takes no size argument",
    "aspect": "not specified; this path takes an aspect ratio, never a pixel size",
}


def home_of(name: str) -> Path:
    gen = GENERATORS[name]
    env = gen.get("home_env")
    return Path(os.environ.get(env) if env and os.environ.get(env)
                else os.path.expanduser(gen["home_default"]))


def blank(text: str) -> bool:
    """Nothing but whitespace — counting a byte-order mark, which str.strip
    keeps and which a prompt file saved by an editor may hold on its own."""
    return not text.replace("\ufeff", "").strip()


def newest_generated(name: str | None = None) -> tuple[str, Path] | None:
    """The newest file left by `name`, or across every generator when unnamed."""
    hits = []
    for n in ([name] if name else GENERATORS):
        for p in home_of(n).glob(GENERATORS[n]["output_glob"]):
            try:                                 # a cache cleared mid-glob, or
                if p.is_file():                  # a dangling link, is not a hit
                    hits.append((p.stat().st_mtime, n, p))
            except OSError:
                continue
    if not hits:
        return None
    _, n, p = max(hits)
    return n, p


def _left_by(where: Path, name: str) -> bool:
    """Whether `where` is a file `name` leaves: under its home, at a path its
    output glob matches whole. Anywhere else under that home — a reference
    image in ~/.codex, a download in a CODEX_HOME set to the user's home — is
    not evidence of who made it. (`match` anchors at the right only, so the
    depth is compared too; `full_match` needs a newer Python than CI runs.)"""
    home = home_of(name).resolve()
    if not where.is_relative_to(home):
        return False
    rel, glob = where.relative_to(home), GENERATORS[name]["output_glob"]
    return len(rel.parts) == len(Path(glob).parts) and rel.match(glob)


def generators_holding(path: Path) -> list[str]:
    """Every generator that leaves files where this one is, the deepest home
    first: one home can sit inside another (a CODEX_HOME set to the user's home)."""
    where = path.resolve()
    held = [n for n in GENERATORS if _left_by(where, n)]
    return sorted(held, key=lambda n: -len(home_of(n).resolve().parts))


def generator_holding(path: Path) -> str | None:
    """The generator whose output directory this file sits in, if any."""
    held = generators_holding(path)
    return held[0] if held else None


# What a placed file's extension promises. A JPEG written to `hero.png` is a
# conversion nobody performed, and every later reader trusts the name.
SUFFIX_FORMAT = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".jpe": "JPEG",
                 ".jfif": "JPEG", ".webp": "WebP", ".gif": "GIF"}


def _searched(name: str | None) -> str:
    return ", ".join(f"{GENERATORS[n]['output_glob']} under {home_of(n)}"
                     for n in ([name] if name else GENERATORS))


def sidecar_of(image: Path) -> Path:
    return image.with_name(image.name + SIDECAR)


# --- capture -----------------------------------------------------------------

def _split_input(spec: str) -> tuple[str, str]:
    """PATH:ROLE, where either half may hold a colon. The split whose path
    exists wins; with none existing, the first colon, as the flag reads. Two
    splits that both name a file are a question, so ValueError says which."""
    cuts = [i for i, c in enumerate(spec) if c == ":"]
    found = [i for i in cuts + [len(spec)]
             if spec[:i] and Path(spec[:i]).expanduser().exists()]
    if len(found) > 1:
        raise ValueError(" and ".join(repr(spec[:i]) for i in found))
    if found:
        return spec[:found[0]], spec[found[0] + 1:]
    return (spec[:cuts[0]], spec[cuts[0] + 1:]) if cuts else (spec, "")


def recorded(path) -> str:
    """A path as a recipe records it: as given, unless it climbs out of the
    directory capture ran in, which no later reader shares — then absolute."""
    # Normalised only to ask the question: `link/../x` names what `link`
    # points beside, so the path as given is what is kept.
    climbs = Path(os.path.normpath(path)).parts[:1] == ("..",)
    return os.path.abspath(path) if climbs else str(path)


def capture(a: argparse.Namespace) -> int:
    if a.generator and a.generator not in GENERATORS:
        print(f"{a.generator} is not one of {sorted(GENERATORS)}", file=sys.stderr)
        return 2
    if a.source:
        held = generators_holding(a.source)
        # Only the deepest home is evidence: a broader one holding it too is
        # the nesting, not a second place the file could have come from.
        deepest = [n for n in held
                   if len(home_of(n).resolve().parts) == len(home_of(held[0]).resolve().parts)]
        if a.generator and held and a.generator not in deepest:
            # The directory is evidence and the flag is a claim; recording the
            # claim would put the wrong invocation in `engine`.
            print(f"{a.source} is in {held[0]}'s output directory, not "
                  f"{a.generator}'s; nothing was written", file=sys.stderr)
            return 2
        src, produced_by = a.source, a.generator or (held[0] if held else None)
        if produced_by is None:
            print(f"{src} is not under any generator's output directory; name "
                  f"the one that made it with --generator {sorted(GENERATORS)}",
                  file=sys.stderr)
            return 2
    else:
        found = newest_generated(a.generator)
        if found is None:
            print(f"nothing matches {_searched(a.generator)}; "
                  "name the file with --from", file=sys.stderr)
            return 2
        produced_by, src = found
    gen = GENERATORS[produced_by]
    # A flag given as whitespace is a field nobody decided; `check` rejects it,
    # so it is refused here, before an asset is placed that a retry cannot replace.
    for flag, value in (("--model", a.model), ("--engine", a.engine),
                        ("--excluded", a.excluded), ("--asked", a.asked)):
        if value is not None and not value.strip():
            print(f"{flag} is blank; leave it out or say what it was", file=sys.stderr)
            return 2
    inputs = []
    for spec in a.input or []:
        try:
            path, role = _split_input(spec)
        except ValueError as e:
            print(f"--input {spec!r} could name either of {e}; rename one, "
                  "or pass a path that names only one", file=sys.stderr)
            return 2
        if not path.strip():
            print(f"--input {spec!r} names no path", file=sys.stderr)
            return 2
        if not Path(path).expanduser().exists():
            # The chain is only as good as its links: a mistyped input is a
            # recipe that points at nothing, and check never opens inputs.
            print(f"--input {spec!r}: {path} does not exist; nothing was written",
                  file=sys.stderr)
            return 2
        inputs.append({"path": recorded(Path(path).expanduser()),
                       "role": role.strip() or "unstated"})
    if not src.exists():
        print(f"{src}: no such file", file=sys.stderr)
        return 2

    dest = a.to
    if dest.is_dir():
        print(f"{dest} is a directory; --to names the file to write", file=sys.stderr)
        return 2
    side = sidecar_of(dest)
    # A link at either name would carry the write somewhere else — outside the
    # project, or over an unrelated file. Placing never follows one.
    try:
        for p in (dest, side):
            if p.is_symlink():
                print(f"{p} is a symbolic link; a capture places files, it does not "
                      "write through links", file=sys.stderr)
                return 2
            p.exists()                       # a name the filesystem refuses, now
    except OSError as e:
        print(f"{e}; nothing was written", file=sys.stderr)
        return 2
    if (dest.exists() or side.exists()) and not a.replace:
        print(f"{dest if dest.exists() else side} already exists. Write a sibling "
              "version instead, or pass --replace once a person has decided to "
              "retire the old one", file=sys.stderr)
        return 2
    if dest.exists() and os.path.samefile(dest, src):
        print(f"{dest} is the generated file itself; place it somewhere else",
              file=sys.stderr)
        return 2

    # Everything that can fail is read before anything is written. A copy
    # placed ahead of a prompt that could not be read is an asset with no
    # recipe, and the overwrite guard then refuses the retry.
    try:
        prompt = (a.prompt_file.read_bytes().decode("utf-8") if a.prompt_file
                  else a.prompt)
        # One read, then that snapshot is what is probed, checked and placed:
        # a generator still rewriting the file cannot swap in other bytes
        # between the check and the copy.
        image = src.read_bytes()
        facts = imgfacts.probe_bytes(image, str(src))
        whole = imgfacts.complete(image)
    except (OSError, UnicodeDecodeError, imgfacts.Unreadable) as e:
        print(f"{e}; nothing was written", file=sys.stderr)
        return 2
    if not whole:
        # The newest-file fallback is exactly where a file still being written
        # is found; a header can be whole long before the picture is.
        print(f"{src} does not reach its end marker — still being written, or "
              "cut short; nothing was written", file=sys.stderr)
        return 2
    if blank(prompt):
        print("the prompt is blank; the prompt is the asset", file=sys.stderr)
        return 2
    promised = SUFFIX_FORMAT.get(dest.suffix.lower())
    if promised != facts["format"]:
        print(f"{src} is {facts['format']}, and {dest.name} names "
              f"{promised or 'no format this checks'}. Place it under its own "
              "extension; a conversion is its own operation and its own line "
              "in the recipe", file=sys.stderr)
        return 2

    doc = {
        "engine": a.engine or gen["invoke"],
        "model": a.model or "unreported",
        "prompt": prompt,
        "excluded": a.excluded or "none",
        "size": {"asked": a.asked or UNASKED[gen["control"]],
                 "on_disk": facts["size"]},
        "inputs": inputs,
        # Absolute, so the field still names the file when read from elsewhere;
        # not resolved, so it is the path the run returned.
        "output": {"generated": os.path.abspath(src), "placed": recorded(dest)},
        "note": NO_SEED,
    }
    try:
        _place(src, image, dest, yaml.safe_dump(doc, sort_keys=False, allow_unicode=True,
                                         default_flow_style=False), a.replace)
    except Stranded as e:
        print(e, file=sys.stderr)
        return 1
    except FileExistsError as e:
        print(f"{e.filename} appeared while this capture ran; nothing was written",
              file=sys.stderr)
        return 2
    except (OSError, shutil.Error) as e:
        print(f"{e}; nothing was written", file=sys.stderr)
        return 2
    print(f"{dest}  {facts['size']}  {facts['bytes']:,} bytes")
    if doc["size"]["asked"] not in (UNASKED[gen["control"]], facts["size"]):
        print(f"  asked for {doc['size']['asked']}, on disk {facts['size']} — "
              "both recorded")
    print(f"{side}  {len(FIELDS)} fields")
    return 0


class Stranded(OSError):
    """A failed capture whose rollback failed too: what it replaced is kept
    under the names this carries, not deleted with the temporaries."""


def _place(src: Path, image: bytes, dest: Path, recipe_text: str, replace: bool) -> None:
    """Put the image and its recipe in place together, or neither.

    Without `replace`, both names are reserved first with O_EXCL — which also
    refuses a link and a capture racing for the same name — then each is
    filled by renaming a finished temporary file over its reservation. With
    `replace`, the files already there are copied aside first. Any failure
    removes whatever this capture created and puts back what it replaced, so
    the result is never an image without its recipe, nor a recipe from
    another run beside it. Captures into one directory hold its lock while
    they place, so two replacing the same name cannot interleave their
    renames and pair one run's image with the other's recipe."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    lock = os.open(dest.parent, os.O_RDONLY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)     # released with the descriptor,
        _place_locked(src, image, dest, recipe_text, replace)   # even if killed
    finally:
        os.close(lock)


def _place_locked(src: Path, image: bytes, dest: Path, recipe_text: str,
                  replace: bool) -> None:
    side = sidecar_of(dest)
    made: list[Path] = []                    # names this capture now owns
    temps: list[str] = []
    kept: dict[Path, str] = {}               # what --replace is replacing
    try:
        if replace:
            for p in (dest, side):
                if p.exists():
                    fd, kept[p] = tempfile.mkstemp(dir=dest.parent, prefix=".capture.")
                    os.close(fd)
                    temps.append(kept[p])
                    shutil.copy2(p, kept[p])
        else:
            for p in (dest, side):
                os.close(os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666))
                made.append(p)
        fd, tmp_img = tempfile.mkstemp(dir=dest.parent, prefix=".capture.")
        temps.append(tmp_img)
        with os.fdopen(fd, "wb") as f:
            f.write(image)                   # the bytes that were checked
        shutil.copystat(src, tmp_img)
        fd, tmp_side = tempfile.mkstemp(dir=dest.parent, prefix=".capture.")
        temps.append(tmp_side)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(recipe_text)
        os.chmod(tmp_side, 0o666 & ~_umask())
        # Owned before the rename, so an interrupt landing between the two
        # still finds the name in `made` and rolls it back.
        made.append(dest)
        os.replace(tmp_img, dest)
        made.append(side)
        os.replace(tmp_side, side)
    except BaseException as failure:
        stranded = []
        for p in dict.fromkeys(reversed(made)):   # undone newest first, once each
            try:
                if p in kept:
                    os.replace(kept[p], p)
                else:
                    Path(p).unlink(missing_ok=True)
            except OSError:
                if p in kept:                # the only copy left: keep it
                    temps.remove(kept[p])
                    stranded.append(f"{p} could not be put back; the original "
                                    f"is saved as {kept[p]}")
                else:
                    stranded.append(f"{p} is from this failed capture and could "
                                    "not be removed")
        if stranded:
            raise Stranded(f"the capture failed ({failure}) and so did undoing it: "
                           f"{'; '.join(stranded)}. Move it back by hand") from failure
        raise
    finally:
        for t in temps:
            try:
                Path(t).unlink(missing_ok=True)
            except OSError:
                pass                         # a leftover temporary must not mask
                                             # the error that is on its way out


def _umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask


# --- check -------------------------------------------------------------------

def check_one(image: Path) -> list[str]:
    side = sidecar_of(image)
    try:
        if not side.exists():
            return [f"{image}: no recipe. Record it as origin: unknown rather than "
                    "reconstructing one — a remembered prompt is a plausible prompt"]
        doc = yaml.safe_load(side.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return [f"{side}: not readable as YAML ({e.__class__.__name__})"]
    except UnicodeDecodeError:
        return [f"{side}: not UTF-8 text; a recipe is written as UTF-8"]
    except OSError as e:                     # one odd entry is one problem, and
        return [f"{side}: {e.strerror or e}"]   # the rest still get checked
    if not isinstance(doc, dict):
        return [f"{side}: a recipe is a mapping of fields, not a "
                f"{type(doc).__name__}; a chain of edits is one recipe per file"]

    problems = []
    for f in FIELDS:
        if f not in doc:
            problems.append(f"{side}: no {f}")
        elif doc[f] in (None, "", {}) and f != "inputs":
            problems.append(f"{side}: {f} is blank — a field nobody decided, "
                            "not one that does not apply")
    if not isinstance(doc.get("prompt"), str) or blank(doc["prompt"]):
        problems.append(f"{side}: prompt must be non-empty text; length cannot prove provenance")
    for f in ("size", "output"):
        if f in doc and not isinstance(doc[f], dict):
            problems.append(f"{side}: {f} must be a mapping, not {doc[f]!r}")
    # Present is not the same as said: each field holds what it is for.
    for f in ("engine", "model", "excluded"):
        if f in doc and doc[f] not in (None, "", {}) and not (
                isinstance(doc[f], str) and doc[f].strip()):
            problems.append(f"{side}: {f} must be text, not {doc[f]!r}")
    if "inputs" in doc and not (isinstance(doc["inputs"], list) and all(
            isinstance(i, dict) and all(isinstance(i.get(k), str) and i[k].strip()
                                        for k in ("path", "role"))
            for i in doc["inputs"])):
        # capture writes "unstated" for a role nobody gave: an absent one is
        # a recipe that lost what the input was for, not one that never said.
        problems.append(f"{side}: inputs must be a list of entries with a path "
                        f"and a role, not {doc['inputs']!r}")
    # Both halves: a recipe holding only what is on disk lost what was asked.
    if isinstance(doc.get("size"), dict):
        asked = doc["size"].get("asked")
        if not (isinstance(asked, str) and asked.strip()):
            problems.append(f"{side}: size.asked must be text, not {asked!r}")
    if isinstance(doc.get("output"), dict):
        for k in ("placed", "generated"):
            v = doc["output"].get(k)
            if not (isinstance(v, str) and v.strip()):
                problems.append(f"{side}: output.{k} must be a path, not {v!r}")
    note = doc.get("note")
    if not isinstance(note, str) or "IRREPRODUCIBLE" not in note:
        problems.append(f"{side}: no note stating IRREPRODUCIBLE — the limit on "
                        "what this recipe promises is stated once, not implied")
    output = doc["output"] if isinstance(doc.get("output"), dict) else {}
    placed = output.get("placed")
    # Resolved from where `capture` ran or from beside the sidecar: the same
    # file, checked from another directory, is still the same file.
    if isinstance(placed, str) and placed.strip() \
            and not _same_file(placed, image, side.parent):
        problems.append(f"{side}: output.placed is {placed}, beside {image}")

    try:
        facts = imgfacts.probe(image)
    except (imgfacts.Unreadable, OSError) as e:
        return problems + [f"{image}: {e}"]
    promised = SUFFIX_FORMAT.get(image.suffix.lower())
    if promised != facts["format"]:
        # What capture refuses to place, a later rename or conversion can
        # still produce; every reader after that trusts the name.
        problems.append(f"{image}: is {facts['format']}, and its name says "
                        f"{promised or 'no format this checks'}")
    size = doc["size"] if isinstance(doc.get("size"), dict) else {}
    on_disk = size.get("on_disk")
    if on_disk != facts["size"]:
        problems.append(f"{side}: size.on_disk is {on_disk!r}, the file is "
                        f"{facts['size']}")
    return problems


def _same_file(placed: str, image: Path, beside: Path) -> bool:
    target = image.resolve()
    p = Path(placed).expanduser()
    if p.is_absolute():
        return p.resolve() == target
    if (Path.cwd() / p).resolve() == target or (beside / p).resolve() == target:
        return True
    # Recorded relative to the directory `capture` ran in: the path's tail
    # still has to name this file, under the same parents as far as it goes.
    # Climbing parts say where that directory was, not what the file is
    # under, so they are not part of the tail (older captures recorded them).
    parts = Path(os.path.normpath(p)).parts
    while parts[:1] == ("..",):
        parts = parts[1:]
    return bool(parts) and target.parts[-len(parts):] == parts


def check(a: argparse.Namespace) -> int:
    targets = list(a.images)
    if a.dir and not a.dir.is_dir():
        print(f"{a.dir} is not a directory", file=sys.stderr)
        return 2
    if a.dir:
        # An image is found by its extension, or by the recipe beside it: a
        # captured file renamed to a suffix that names no format is still one
        # this check has to see, and say so.
        targets += [p for p in sorted(a.dir.rglob("*"))
                    if p.is_file() and not p.name.endswith(SIDECAR)
                    and (p.suffix.lower() in SUFFIX_FORMAT or sidecar_of(p).exists())]
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
        try:
            print(side.read_text(encoding="utf-8") if side.exists()
                  else "origin: unknown   # no recipe beside this file")
        except UnicodeDecodeError:
            print(f"{side}: not UTF-8 text")
        except OSError as e:
            print(f"{side}: {e.strerror or e}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("capture", help="copy a generated file into the project "
                                       "and write its recipe")
    c.add_argument("--to", required=True, type=Path)
    c.add_argument("--from", dest="source", type=Path,
                   help="default: the newest file any generator left")
    c.add_argument("--generator", choices=sorted(GENERATORS),
                   help="which generator produced it; default: whichever left "
                        "the newest file")
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
