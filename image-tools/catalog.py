#!/usr/bin/env python3
"""Generate an asset catalogue from image files and their existing recipes.

    python3 catalog.py --dir assets --out .agents/asset-catalog.html
    python3 catalog.py --dir assets --out .agents/asset-catalog.json --format json

The catalogue measures files; it does not review their pixels, invent an origin,
or copy prompts into a public page. Image and recipe links are relative to the
output. Directory symlinks are skipped; file symlinks must stay inside --dir.
No source is changed, and any invalid image or recipe prevents publication.
"""
from __future__ import annotations

import argparse
import contextlib
import html
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True
import imgfacts                                            # noqa: E402
import recipe                                              # noqa: E402


class Refused(Exception):
    """The catalogue cannot be published without hiding a problem."""


def _relative(path: Path, base: Path) -> str:
    return Path(os.path.relpath(path, base)).as_posix()


def _url(path: Path, output: Path) -> str:
    return quote(_relative(path, output.parent), safe="/")


def _regular(path: Path, root: Path) -> Path:
    """Resolve an input without accepting an outside link or a special file."""
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except ValueError as e:
        raise Refused(f"{path}: symlink leaves the asset directory") from e
    except (OSError, RuntimeError) as e:
        raise Refused(f"{path}: cannot resolve input ({e})") from e
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise Refused(f"{path}: not a regular file")
    return resolved


def _read_image(path: Path, root: Path) -> bytes:
    resolved = _regular(path, root)
    # Nonblocking open also refuses a FIFO substituted after the stat, without
    # hanging the run. O_NOFOLLOW protects the final name from a substituted link.
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(resolved, flags)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise Refused(f"{path}: not a regular file")
        return stream.read()


def _files(directory: Path, problems: list[str]) -> list[Path]:
    """Walk actual directories only, retaining links for input validation."""
    found = []
    try:
        with os.scandir(directory) as entries:
            ordered = sorted(entries, key=lambda entry: entry.name)
        for entry in ordered:
            path = directory / entry.name
            try:
                mode = entry.stat(follow_symlinks=False).st_mode
                if stat.S_ISDIR(mode):
                    found.extend(_files(path, problems))
                elif stat.S_ISLNK(mode) and entry.is_dir():
                    continue  # including directory links to somewhere inside --dir
                elif stat.S_ISREG(mode) or stat.S_ISLNK(mode):
                    found.append(path)
                else:
                    problems.append(f"{path}: not a regular file; special files are not read")
            except OSError as e:
                problems.append(f"{path}: {e}")
    except OSError as e:
        problems.append(f"{directory}: cannot list directory ({e})")
    return found


def collect(directory: Path, output: Path) -> tuple[dict, list[str]]:
    """Collect deterministic measured records; return all observed problems.

    Paths in assets are relative to the input root. URLs and the document's root
    are relative to the output's parent, so the catalogue travels with a project.
    A recipe status of checked means its fields and dimensions passed recipe.py;
    it is not proof of invocation provenance or of the image's visual quality.
    """
    directory, output = Path(directory), Path(os.path.abspath(output))
    problems: list[str] = []
    doc = {"schema_version": 1, "root": _relative(directory.absolute(), output.parent),
           "assets": []}
    try:
        root = directory.resolve(strict=True)
        if not root.is_dir():
            raise Refused(f"{directory}: not a directory")
    except (OSError, RuntimeError, Refused) as e:
        return doc, [str(e)]
    doc["root"] = _relative(root, output.parent)
    files = _files(root, problems)
    # Sidecars discover renamed images too, and an orphan sidecar is a broken
    # reference to report rather than a recipe silently left out of the set.
    targets = {p for p in files if p.suffix.lower() in recipe.SUFFIX_FORMAT}
    targets.update(p.with_name(p.name[:-len(recipe.SIDECAR)]) for p in files
                   if p.name.endswith(recipe.SIDECAR) and p.name != recipe.SIDECAR)
    for image in sorted(targets, key=lambda p: p.relative_to(root).as_posix()):
        side = recipe.sidecar_of(image)
        try:
            raw = _read_image(image, root)
            facts = imgfacts.probe_bytes(raw, str(image))
            if not imgfacts.complete(raw):
                raise Refused(f"{image}: does not reach its end marker; image is cut short")
            promised = recipe.SUFFIX_FORMAT.get(image.suffix.lower())
            if promised != facts["format"]:
                raise Refused(f"{image}: is {facts['format']}, and its name says "
                              f"{promised or 'no supported image format'}")
        except (OSError, RuntimeError, imgfacts.Unreadable, Refused) as e:
            problems.append(str(e))
            continue
        provenance = {"status": "unknown", "path": None, "url": None}
        if os.path.lexists(side):
            provenance.update(status="invalid", path=side.relative_to(root).as_posix(),
                              url=_url(side, output))
            try:
                _regular(side, root)
                errors = recipe.check_one(image)
                problems.extend(errors)
                if not errors:
                    provenance["status"] = "checked"
            except (OSError, RuntimeError, ValueError, Refused) as e:
                problems.append(str(e))
        doc["assets"].append({
            "path": image.relative_to(root).as_posix(), "url": _url(image, output),
            "format": facts["format"], "width": facts["width"], "height": facts["height"],
            "size": facts["size"], "displayed_size": facts.get("displayed", facts["size"]),
            "orientation": facts.get("orientation", 1), "bytes": facts["bytes"],
            "alpha": facts["alpha"], "colour": facts["colour"], "recipe": provenance,
        })
    return doc, problems


def render_html(document: dict) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    cards = []
    for asset in document["assets"]:
        provenance = asset["recipe"]
        recipe_link = (f'<a href="{esc(provenance["url"])}">Recipe: {esc(provenance["status"])}</a>'
                       if provenance["url"] else '<span>Recipe: unknown</span>')
        facts = [("Format", asset["format"]), ("Stored", asset["size"]),
                 ("Displayed", asset["displayed_size"]), ("Bytes", f'{asset["bytes"]:,}'),
                 ("Alpha", "yes" if asset["alpha"] else "no"), ("Colour", asset["colour"])]
        details = "".join(f"<div><dt>{label}</dt><dd>{esc(value)}</dd></div>" for label, value in facts)
        cards.append(f'''<article class="asset">
<a class="preview" href="{esc(asset['url'])}"><img src="{esc(asset['url'])}" alt="{esc(Path(asset['path']).name)}" loading="lazy"></a>
<div class="details"><h2><a href="{esc(asset['url'])}">{esc(asset['path'])}</a></h2>
<dl>{details}</dl><div class="recipe">{recipe_link}</div></div>
</article>''')
    count = len(document["assets"])
    contents = "\n".join(cards) if cards else '<p class="empty">No image assets found.</p>'
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Asset catalogue</title>
<style>
:root {{ color-scheme: light dark; font-family: system-ui, sans-serif; background: #f4f6f8; color: #172436; }}
* {{ box-sizing: border-box; }}
body {{ max-width: 1440px; margin: 0 auto; padding: 36px 24px; }}
header {{ margin-bottom: 28px; }}
h1 {{ margin: 0 0 8px; font-size: 2rem; letter-spacing: -.04em; }}
header p, footer {{ max-width: 90ch; line-height: 1.6; color: #526174; }}
code {{ overflow-wrap: anywhere; }}
a {{ color: #205b9b; text-decoration-thickness: 1px; text-underline-offset: 3px; }}
main {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(min(300px, 100%), 1fr)); gap: 20px; }}
.asset {{ overflow: hidden; background: #fff; border: 1px solid #dce3eb; border-radius: 14px; }}
.preview {{ display: flex; align-items: center; justify-content: center; height: 220px; padding: 12px; background-color: #e8edf2;
  background-image: linear-gradient(45deg, #dbe2e9 25%, transparent 25%), linear-gradient(-45deg, #dbe2e9 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #dbe2e9 75%), linear-gradient(-45deg, transparent 75%, #dbe2e9 75%);
  background-size: 20px 20px; background-position: 0 0, 0 10px, 10px -10px, -10px 0; }}
img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
.details {{ padding: 18px; }}
h2 {{ margin: 0 0 14px; font-size: 1rem; overflow-wrap: anywhere; }}
dl {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 0; }}
dt {{ color: #526174; font-size: .75rem; }}
dd {{ margin: 3px 0 0; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; font-size: .9rem; }}
.recipe {{ margin-top: 18px; font-size: .85rem; }}
footer {{ margin-top: 30px; font-size: .85rem; }}
.empty {{ padding: 24px; background: #fff; border-radius: 12px; }}
@media (prefers-color-scheme: dark) {{
 :root {{ background: #121922; color: #e7edf5; }}
 .asset, .empty {{ background: #1d2734; border-color: #354254; }}
 header p, footer, dt {{ color: #aab8c9; }}
 a {{ color: #96c7ff; }}
}}
</style>
</head>
<body>
<header><h1>Asset catalogue</h1><p>{count} image{'s' if count != 1 else ''} · <code>{esc(document['root'])}</code></p>
<p>File properties are measured from image headers. This catalogue does not certify visual quality. Recipe links keep the original record separate.</p></header>
<main>{contents}</main>
<footer>Directory symlinks are skipped. Preview labels are filenames, not alternative text for a product's use of an image.
“Recipe: checked” means fields and dimensions passed validation; “unknown” means no sidecar was found. Prompts are not copied into this page.</footer>
</body>
</html>
'''


def _output_state(output: Path, format_name: str, replace: bool):
    if output.suffix.lower() != "." + format_name:
        raise Refused(f"{output}: --format {format_name} requires a .{format_name} output")
    # Do not traverse a symlinked parent, including one above a missing parent.
    for parent in reversed(output.parents):
        if parent.is_symlink():
            raise Refused(f"{parent}: output directory is a symlink")
        if parent.exists() and not parent.is_dir():
            raise Refused(f"{parent}: output parent is not a directory")
    if output.is_symlink():
        raise Refused(f"{output}: output is a symlink")
    if os.path.lexists(recipe.sidecar_of(output)):
        raise Refused(f"{output}: has an image recipe; cannot replace an asset")
    try:
        info = output.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode):
        raise Refused(f"{output}: output is not a regular file")
    if info.st_nlink != 1:
        raise Refused(f"{output}: output has hard links")
    if not replace:
        raise Refused(f"{output}: already exists; use --replace to update the catalogue")
    # A misleading suffix is not permission to overwrite image data.
    try:
        imgfacts.probe(output)
    except imgfacts.Unreadable:
        pass
    else:
        raise Refused(f"{output}: contains an image; cannot replace an asset")
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def publish(output: Path, text: str, format_name: str, replace: bool) -> None:
    """Publish one complete file, preserving an existing output on any failure."""
    output = Path(os.path.abspath(output))
    before = _output_state(output, format_name, replace)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         prefix=".asset-catalog-", suffix=".tmp",
                                         dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if _output_state(output, format_name, replace) != before:
            raise Refused(f"{output}: changed while the catalogue was being written")
        if before is None:
            # Unlike rename, creating a hard link refuses a file that appeared
            # after validation. The temporary name is then removed in finally.
            os.link(temporary, output)
        else:
            os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", required=True, type=Path, help="asset directory; directory symlinks are skipped")
    parser.add_argument("--out", required=True, type=Path, help="catalogue path (.html or .json)")
    parser.add_argument("--format", choices=("html", "json"), default="html")
    parser.add_argument("--replace", action="store_true", help="replace an existing catalogue")
    args = parser.parse_args(argv)
    with contextlib.suppress(AttributeError, ValueError):
        sys.stderr.reconfigure(errors="backslashreplace")
        sys.stdout.reconfigure(errors="backslashreplace")
    try:
        document, problems = collect(args.dir, args.out)
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            return 1
        content = (render_html(document) if args.format == "html" else
                   json.dumps(document, ensure_ascii=False, indent=2) + "\n")
        publish(args.out, content, args.format, args.replace)
    except (OSError, RuntimeError, UnicodeError, Refused) as e:
        print(e, file=sys.stderr)
        return 1
    print(f"{len(document['assets'])} image(s): {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
