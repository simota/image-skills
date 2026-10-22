#!/usr/bin/env python3
"""Prove the tools read what is actually there.

`imgfacts.py` is what turns a claim about an image from `asserted` into
`measured`, so a bug in it does not produce a wrong answer — it produces a
confident one. `recipe.py` is what keeps a picture usable by anyone after you.
`strip.py` edits files that ship, and its two ways to be wrong are opposite:
leaving something in that should have gone, and taking something out that
should have stayed. None of the three is a check, so none is covered by
`test_validate.py` or `test_figures.py`; this is their harness.

    make tools-test

The PNG fixtures are real files, built here with `zlib` and decodable by
anything. The JPEG, WebP and GIF fixtures are headers only: these tools parse
headers and never touch pixel data, and saying so is better than pretending a
handmade JPEG is a photograph.
"""
from __future__ import annotations

import contextlib
import io
import json
import struct
import sys
import subprocess
import tempfile
import zlib
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True
import imgfacts                                            # noqa: E402
import engine                                              # noqa: E402
import recipe                                              # noqa: E402
import refute                                              # noqa: E402
import render                                              # noqa: E402
import strip                                               # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"  {name}: got {got!r}, want {want!r}")


def truthy(name: str, got) -> None:
    if not got:
        failures.append(f"  {name}: got {got!r}, want something truthy")


# --- fixtures ----------------------------------------------------------------

def png(w: int, h: int, colour: int = 2, extra: bytes = b"") -> bytes:
    """A real, decodable PNG. `colour` is the PNG colour type."""
    def chunk(tag: bytes, body: bytes) -> bytes:
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colour]
    row = b"\x00" + b"\x7f" * (w * channels)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, colour, 0, 0, 0)
    body = chunk(b"IHDR", ihdr) + extra
    if colour == 3:
        body += chunk(b"PLTE", b"\xff\x00\x00")
    return (imgfacts.PNG_SIG + body
            + chunk(b"IDAT", zlib.compress(row * h)) + chunk(b"IEND", b""))


def raw_chunk(tag: bytes, body: bytes) -> bytes:
    return (struct.pack(">I", len(body)) + tag + body
            + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))


def srgb_chunk() -> bytes:
    return raw_chunk(b"sRGB", b"\x00")


def trns_chunk() -> bytes:
    """Keyed transparency. An indexed PNG carries alpha here and nowhere in its
    colour type, which is how a sprite or an icon usually stores it."""
    return raw_chunk(b"tRNS", b"\x00")


def jpeg(w: int, h: int, icc: bool = False, progressive: bool = False) -> bytes:
    """Headers only — enough for a header parser, and not a decodable image."""
    out = b"\xff\xd8"
    if icc:
        body = b"ICC_PROFILE\x00" + b"\x01\x01" + b"\x00" * 8
        out += b"\xff\xe2" + struct.pack(">H", len(body) + 2) + body
    sof = b"\xff\xc2" if progressive else b"\xff\xc0"
    body = b"\x08" + struct.pack(">HH", h, w) + b"\x01\x01\x11\x00"
    out += sof + struct.pack(">H", len(body) + 2) + body
    return out + b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"


def webp_vp8x(w: int, h: int, alpha: bool, icc: bool) -> bytes:
    flags = (0x10 if alpha else 0) | (0x20 if icc else 0)
    body = (bytes([flags]) + b"\x00\x00\x00"
            + (w - 1).to_bytes(3, "little") + (h - 1).to_bytes(3, "little"))
    chunk = b"VP8X" + struct.pack("<I", len(body)) + body
    return b"RIFF" + struct.pack("<I", 4 + len(chunk)) + b"WEBP" + chunk


def webp_vp8l(w: int, h: int, alpha: bool) -> bytes:
    bits = (w - 1) | ((h - 1) << 14) | (int(alpha) << 28)
    body = b"\x2f" + struct.pack("<I", bits)
    chunk = b"VP8L" + struct.pack("<I", len(body)) + body + b"\x00"   # RIFF pad
    return b"RIFF" + struct.pack("<I", 4 + len(chunk)) + b"WEBP" + chunk


def gif(w: int, h: int) -> bytes:
    return b"GIF89a" + struct.pack("<HH", w, h) + b"\x00\x00\x00"


def exif(orientation: int | None) -> bytes:
    """A little-endian TIFF block, optionally stating an orientation."""
    entries = b""
    if orientation is not None:
        entries = struct.pack("<HHIHH", 0x0112, 3, 1, orientation, 0)
    n = 1 if orientation is not None else 0
    return (b"II\x2a\x00" + struct.pack("<I", 8)
            + struct.pack("<H", n) + entries + struct.pack("<I", 0))


def jpeg_with(w: int, h: int, segments: list[tuple[int, bytes]],
              pad: bytes = b"") -> bytes:
    """`pad` goes before every marker — fill bytes, a standalone marker, or both."""
    out = b"\xff\xd8"
    for marker, body in segments:
        out += pad + bytes([0xFF, marker]) + struct.pack(">H", len(body) + 2) + body
    body = b"\x08" + struct.pack(">HH", h, w) + b"\x01\x01\x11\x00"
    out += pad + b"\xff\xc0" + struct.pack(">H", len(body) + 2) + body
    return out + b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00" + b"ENTROPY" + b"\xff\xd9"


def webp_with(w: int, h: int, flags: int, chunks: list[tuple[bytes, bytes]]) -> bytes:
    head = (bytes([flags]) + b"\x00\x00\x00"
            + (w - 1).to_bytes(3, "little") + (h - 1).to_bytes(3, "little"))
    body = b"WEBP" + b"VP8X" + struct.pack("<I", len(head)) + head
    for tag, payload in chunks:
        pad = b"\x00" if len(payload) & 1 else b""
        body += tag + struct.pack("<I", len(payload)) + payload + pad
    return b"RIFF" + struct.pack("<I", len(body)) + body


def refuses(path: Path, opt, fragment: str) -> bool:
    """True when strip refuses `path` for a reason containing `fragment`."""
    try:
        strip.strip(path, opt)
        return False
    except strip.Refused as e:
        return fragment in str(e)


class Opt:
    """The flags strip.main() would have parsed."""

    def __init__(self, **kw):
        self.drop_profile = kw.get("drop_profile", False)
        self.drop_credentials = kw.get("drop_credentials", False)
        self.orientation_is_applied = kw.get("orientation_is_applied", False)


# --- imgfacts ----------------------------------------------------------------

def test_imgfacts(tmp: Path) -> None:
    cases = [
        ("png truecolour", png(64, 32), dict(format="PNG", size="64x32",
                                             ratio="2:1", alpha=False)),
        ("png with alpha", png(16, 16, colour=6), dict(format="PNG", alpha=True)),
        ("png greyscale+alpha", png(16, 16, colour=4), dict(alpha=True)),
        ("png indexed", png(16, 16, colour=3), dict(alpha=False)),
        ("png indexed with tRNS", png(16, 16, colour=3, extra=trns_chunk()),
         dict(format="PNG", alpha=True)),
        ("png truecolour with tRNS", png(16, 16, extra=trns_chunk()),
         dict(alpha=True)),
        ("png srgb tagged", png(16, 16, extra=srgb_chunk()),
         dict(colour="sRGB tagged")),
        ("png untagged", png(16, 16), dict(colour="none declared")),
        ("jpeg baseline", jpeg(1536, 1024), dict(format="JPEG", size="1536x1024",
                                                 ratio="3:2", alpha=False)),
        ("jpeg with icc", jpeg(64, 64, icc=True), dict(colour="ICC embedded")),
        ("webp extended", webp_vp8x(1024, 768, alpha=True, icc=True),
         dict(format="WebP", size="1024x768", alpha=True, colour="ICC embedded")),
        ("webp lossless", webp_vp8l(300, 200, alpha=True),
         dict(format="WebP", size="300x200", alpha=True)),
        ("gif", gif(120, 90), dict(format="GIF", size="120x90", ratio="4:3")),
    ]
    for name, raw, want in cases:
        f = tmp / f"{name.replace(' ', '_')}.bin"
        f.write_bytes(raw)
        got = imgfacts.probe(f)
        for k, v in want.items():
            check(f"{name}.{k}", got[k], v)

    facts = imgfacts.probe(tmp / "jpeg_baseline.bin")
    check("megapixels", facts["megapixels"], 1.57)
    check("bytes match the file", facts["bytes"],
          (tmp / "jpeg_baseline.bin").stat().st_size)
    truthy("sha256 present", facts["sha256"])
    truthy("progressive is noted",
           "progressive" in notes_of(tmp, jpeg(8, 8, progressive=True)))

    junk = tmp / "junk.png"
    junk.write_bytes(b"not an image at all")
    try:
        imgfacts.probe(junk)
        failures.append("  junk file: probe returned instead of raising")
    except imgfacts.Unreadable:
        pass
    check("junk exits non-zero, no traceback",
          imgfacts.main([str(junk)]), 1)


def notes_of(tmp: Path, raw: bytes) -> list[str]:
    f = tmp / "note.bin"
    f.write_bytes(raw)
    return imgfacts.probe(f)["notes"]


# --- canvas legality ---------------------------------------------------------

def test_legality() -> None:
    check("legal size", imgfacts.illegal(1536, 1024), set())
    check("not a multiple of 16", imgfacts.illegal(1000, 1000), {"multiple of 16"})
    check("too few pixels", imgfacts.illegal(512, 512), {"total pixels"})
    check("too wide", imgfacts.illegal(3840, 1024), {"ratio"})
    check("over the edge", imgfacts.illegal(4096, 2304),
          {"max edge", "total pixels"})

    near = imgfacts.nearest_legal(1000, 1000)
    truthy("a nearest size exists for 1000x1000", near)
    check("the nearest size is legal", imgfacts.illegal(*near), set())
    check("no legal size past the ratio limit",
          imgfacts.nearest_legal(3840, 1024), None)
    for w, h in ((512, 512), (4096, 2304), (999, 1001)):
        n = imgfacts.nearest_legal(w, h)
        truthy(f"nearest_legal({w},{h}) answers", n)
        if n:
            check(f"nearest_legal({w},{h}) is legal", imgfacts.illegal(*n), set())

    # nearest, and still the same shape. A review found this picking a canvas
    # four times the area for a fourth decimal place of aspect.
    for w, h in ((999, 1001), (1919, 1079), (4096, 2304), (1000, 500),
                 (700, 300), (512, 512), (3000, 1005)):
        n = imgfacts.nearest_legal(w, h)
        truthy(f"nearest_legal({w},{h}) answers", n)
        check(f"nearest_legal({w},{h}) is legal", imgfacts.illegal(*n), set())
        drift = abs(n[0] / n[1] - w / h) / (w / h)
        # 1% is this test's own number, not the module's. Asserting against
        # imgfacts.ASPECT_TOLERANCE would pass for any value the module chose,
        # including one that lets the shape change completely.
        truthy(f"nearest_legal({w},{h}) keeps the shape, within 1%", drift <= 0.01)
        truthy(f"nearest_legal({w},{h}) is near in area",
               n[0] * n[1] <= max(4 * w * h, imgfacts.CANVAS["min_pixels"] * 1.3))
    check("a size already legal is returned unchanged",
          imgfacts.nearest_legal(1536, 1024), (1536, 1024))
    # where the grid offers nothing inside the band, the least-drifting legal
    # candidate is still returned rather than nothing
    truthy("a legal answer exists even at an awkward aspect",
           imgfacts.nearest_legal(1021, 1019))

    check("--check-size exits 0 on a legal size",
          imgfacts.main(["--check-size", "1536x1024"]), 0)
    check("--check-size exits 1 on an illegal one",
          imgfacts.main(["--check-size", "1000x1000"]), 1)
    check("--check-size rejects nonsense", imgfacts.main(["--check-size", "big"]), 2)


def test_nearest_legal_at_the_edge() -> None:
    """The nearest legal canvas can sit just under the edge limit, below both
    grid heights nearest the aspect. A review found 2251x5653 answered with
    1520x3824 when 1536x3840 is legal, the same shape, and nearer in area."""
    check("the legal height under max_edge is considered",
          imgfacts.nearest_legal(2251, 5653), (1536, 3840))


def test_aspect_legality() -> None:
    """The other generator's only size lever, and the reduce-then-compare that
    makes `1920:1080` and `16:9` the same question."""
    name = sorted(imgfacts.ASPECT_GENERATORS)[0]
    offered = imgfacts.aspect_offered(name)
    truthy("the aspect list is not empty", offered)
    for spec in offered:
        a, b = (int(x) for x in spec.split(":"))
        check(f"{spec} is already reduced", imgfacts.aspect_of(a, b), spec)
    check("a size reduces to its aspect", imgfacts.aspect_of(1920, 1080), "16:9")
    check("an off-list shape gets the nearest on-list one",
          imgfacts.nearest_aspect("5:4", name), "4:3")
    truthy("an unknown generator raises rather than answering",
           raises(lambda: imgfacts.aspect_offered("nobody"), KeyError))

    check("--check-aspect exits 0 on an offered shape",
          imgfacts.main(["--check-aspect", "16:9"]), 0)
    check("--check-aspect reduces before comparing",
          imgfacts.main(["--check-aspect", "1920:1080"]), 0)
    check("--check-aspect exits 1 on one that is not offered",
          imgfacts.main(["--check-aspect", "5:4", "--json"]), 1)
    check("--check-aspect rejects nonsense",
          imgfacts.main(["--check-aspect", "wide"]), 2)
    saved = dict(imgfacts.ASPECT_GENERATORS)
    imgfacts.ASPECT_GENERATORS["second"] = {"aspects": ["5:4"]}
    try:
        check("with two aspect generators, --check-aspect asks which is meant",
              imgfacts.main(["--check-aspect", "5:4"]), 2)
        check("and answers once it is told",
              imgfacts.main(["--check-aspect", "5:4", "--generator", "second"]), 0)
    finally:
        imgfacts.ASPECT_GENERATORS.clear()
        imgfacts.ASPECT_GENERATORS.update(saved)
    check("--check-aspect refuses a generator that has no aspect list",
          imgfacts.main(["--check-aspect", "1:1", "--generator",
                         imgfacts.CANVAS_GENERATOR]), 2)


def raises(fn, kind) -> bool:
    try:
        fn()
    except kind:
        return True
    return False


# --- recipe ------------------------------------------------------------------

PROMPT = "Use case: stylized-concept\nPrimary request: a red circle"


def capture(tmp: Path, dest: str, replace: bool = False, **kw) -> int:
    src = tmp / "src.png"
    src.write_bytes(png(64, 32))
    args = ["capture", "--to", str(tmp / dest), "--from", str(src),
            "--prompt", kw.pop("prompt", PROMPT),
            "--generator", kw.pop("generator", recipe.DEFAULT_GENERATOR)]
    for k, v in kw.items():
        args += [f"--{k.replace('_', '-')}", str(v)]
    if replace:
        args.append("--replace")
    return recipe.main(args)


def without(side: Path, field: str) -> None:
    """Drop one field, through YAML rather than by line.

    Deleting the `prompt: |` line leaves its indented body behind and tests
    something else entirely — which is what the first version of this did."""
    doc = yaml.safe_load(side.read_text(encoding="utf-8"))
    doc.pop(field)
    side.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def test_recipe(tmp: Path) -> None:
    check("capture writes", capture(tmp, "hero.png", excluded="text"), 0)
    side = tmp / ("hero.png" + recipe.SIDECAR)
    truthy("the sidecar exists", side.exists())
    truthy("the size is read off the file", "on_disk: 64x32" in side.read_text())
    check("a complete recipe checks out", recipe.check_one(tmp / "hero.png"), [])

    check("capture refuses to overwrite", capture(tmp, "hero.png"), 2)
    check("--replace is how a person decides",
          capture(tmp, "hero.png", replace=True), 0)

    good = side.read_text()
    for field in recipe.FIELDS:                # every field, one at a time
        without(side, field)
        truthy(f"a missing {field} is reported",
               any(f"no {field}" in p for p in recipe.check_one(tmp / "hero.png")))
        side.write_text(good)

    for field in ("engine", "model", "excluded"):
        doc = yaml.safe_load(good)
        doc[field] = ""
        side.write_text(yaml.safe_dump(doc, sort_keys=False))
        truthy(f"a blank {field} is reported",
               any("blank" in p for p in recipe.check_one(tmp / "hero.png")))
        side.write_text(good)

    # the size on disk is compared against the file, not trusted
    side.write_text(good.replace("on_disk: 64x32", "on_disk: 1536x1024"))
    truthy("a size that does not match the file is reported",
           any("64x32" in p for p in recipe.check_one(tmp / "hero.png")))
    side.write_text(good)

    # Length cannot distinguish a sent prompt from a summary; type can.
    for value in (17, [], "   ", "\ufeff\n"):
        doc = yaml.safe_load(good)
        doc["prompt"] = value
        side.write_text(yaml.safe_dump(doc, sort_keys=False))
        truthy("non-text/blank prompts are reported",
               any("non-empty text" in p for p in recipe.check_one(tmp / "hero.png")))
    side.write_text(good)

    # an image with no recipe is not silently fine
    (tmp / "orphan.png").write_bytes(png(16, 16))
    truthy("an image with no recipe is reported",
           any("no recipe" in p for p in recipe.check_one(tmp / "orphan.png")))
    check("check --dir exits non-zero when something is missing",
          recipe.main(["check", "--dir", str(tmp)]), 1)
    check("capture without a prompt is refused", capture_no_prompt(tmp), 2)


def test_recipe_verbatim(tmp: Path) -> None:
    """Capture must not normalize a request or infer its truth from its length.
    Synthetic PNG headers test file properties, not visual inspection.
    """
    texts = ["red dot", "赤い丸", "first\nsecond", "first\nsecond\n",
             "first\nsecond\n\n", "first\r\nsecond\r\n", "  red dot  "]
    for i, text in enumerate(texts):
        dest = f"verbatim-{i}.png"
        check(f"short/exact prompt {i} captured", capture(tmp, dest, prompt=text), 0)
        doc = yaml.safe_load((tmp / (dest + recipe.SIDECAR)).read_text())
        check(f"submitted prompt {i} survives exactly", doc["prompt"], text)
        check(f"short/exact prompt {i} validates", recipe.check_one(tmp / dest), [])
    prompt_file = tmp / "request.txt"
    raw = "Text: 春\r\nAvoid: text elsewhere\r\n\r\n".encode("utf-8")
    prompt_file.write_bytes(raw)
    dest = tmp / "from-prompt-file.png"
    check("capture prompt file", recipe.main([
        "capture", "--from", str(tmp / "src.png"), "--to", str(dest),
        "--prompt-file", str(prompt_file), "--generator", "codex"]), 0)
    doc = yaml.safe_load(recipe.sidecar_of(dest).read_text())
    check("file line endings survive exactly", doc["prompt"].encode("utf-8"), raw)
    check("unreported model is honest absence", doc["model"], "unreported")
    check("file prompt validates", recipe.check_one(dest), [])


def test_recipe_generators(tmp: Path) -> None:
    """Which generator produced the file changes what the recipe says about it.

    `engine` and the `size.asked` placeholder are both read off the named
    generator, so a run captured under the wrong one would record a command
    nobody ran and a reason for the missing size that does not apply to it.
    """
    for name, gen in recipe.GENERATORS.items():
        dest = f"by-{name}.png"
        check(f"capture --generator {name} writes", capture(tmp, dest, generator=name), 0)
        side = (tmp / (dest + recipe.SIDECAR)).read_text(encoding="utf-8")
        truthy(f"{name}'s own invocation is recorded", gen["invoke"] in side)
        truthy(f"{name}'s missing size says why it is missing",
               recipe.UNASKED[gen["control"]] in side)
    check("an unknown generator is refused, not defaulted",
          capture_unknown_generator(tmp), 2)


def capture_unknown_generator(tmp: Path) -> int:
    try:
        return recipe.main(["capture", "--to", str(tmp / "y.png"), "--from",
                            str(tmp / "src.png"), "--prompt", PROMPT,
                            "--generator", "nobody"])
    except SystemExit as e:                    # argparse rejects the choice
        return e.code


def capture_no_prompt(tmp: Path) -> int:
    try:
        recipe.main(["capture", "--to", str(tmp / "x.png"), "--from",
                     str(tmp / "src.png")])
    except SystemExit as e:                    # argparse .error() exits 2
        return e.code
    return 0


def test_recipe_hardening(tmp: Path) -> None:
    """Capture writes nothing it cannot finish, and check reads what it is given."""
    import os
    d = tmp / "hard"
    d.mkdir()
    src = d / "src.png"
    src.write_bytes(png(64, 32))

    def cap(*extra: str) -> int:
        return recipe.main(["capture", "--from", str(src), *extra])

    check("a prompt file that is missing is refused",
          cap("--to", str(d / "a.png"), "--generator", "codex",
              "--prompt-file", str(d / "nope.txt")), 2)
    check("and nothing was placed for the retry to trip over",
          (d / "a.png").exists(), False)
    (d / "latin1.txt").write_bytes(b"caf\xe9")
    check("a prompt file that is not UTF-8 is refused",
          cap("--to", str(d / "a.png"), "--generator", "codex",
              "--prompt-file", str(d / "latin1.txt")), 2)
    check("a blank prompt is refused at capture, not left for check",
          cap("--to", str(d / "a.png"), "--generator", "codex", "--prompt", "   "), 2)
    (d / "bom.txt").write_bytes(b"\xef\xbb\xbf\n")
    check("a prompt file holding only a byte-order mark is blank too",
          cap("--to", str(d / "a.png"), "--generator", "codex",
              "--prompt-file", str(d / "bom.txt")), 2)
    check("--from outside every generator's directory needs --generator",
          cap("--to", str(d / "a.png"), "--prompt", PROMPT), 2)
    check("a PNG placed under .jpg is refused",
          cap("--to", str(d / "a.jpg"), "--generator", "codex", "--prompt", PROMPT), 2)
    check("a directory is not a destination",
          cap("--to", str(d), "--generator", "codex", "--prompt", PROMPT, "--replace"), 2)
    check("the generated file is not its own destination",
          cap("--to", str(src), "--generator", "codex", "--prompt", PROMPT, "--replace"), 2)
    recipe.sidecar_of(d / "b.png").write_text("engine: x\n", encoding="utf-8")
    check("an orphan recipe is not overwritten silently",
          cap("--to", str(d / "b.png"), "--generator", "codex", "--prompt", PROMPT), 2)

    home = d / "codex-home"
    out = home / "generated_images" / "s1"
    out.mkdir(parents=True)
    (out / "exec-1.png").write_bytes(png(32, 32))
    (out / "exec-2.png").symlink_to(out / "gone.png")      # dangling: not a hit
    old = os.environ.get("CODEX_HOME")
    os.environ["CODEX_HOME"] = str(home)
    try:
        check("a dangling link in the output directory does not crash the search",
              recipe.newest_generated("codex")[1].name, "exec-1.png")
        check("a file under a generator's directory is attributed to it",
              recipe.generator_holding(out / "exec-1.png"), "codex")
    finally:
        if old is None:
            os.environ.pop("CODEX_HOME")
        else:
            os.environ["CODEX_HOME"] = old

    check("capture writes", cap("--to", str(d / "c.png"), "--generator", "codex",
                                "--prompt", PROMPT), 0)
    side = recipe.sidecar_of(d / "c.png")
    good = side.read_text(encoding="utf-8")
    here = Path.cwd()
    try:
        os.chdir(d)
        check("the same file checked from its own directory is still the same file",
              recipe.check_one(Path("c.png")), [])
    finally:
        os.chdir(here)
    check("and checked by absolute path", recipe.check_one((d / "c.png").resolve()), [])

    for text, says in (("just a string\n", "mapping"), ("- a: 1\n- b: 2\n", "mapping"),
                       (good.replace("size:", "size: 64x32\nold_size:"), "size must"),
                       (good.replace("note:", "old_note:"), "IRREPRODUCIBLE")):
        side.write_text(text, encoding="utf-8")
        truthy(f"a malformed recipe is reported ({says}), not a traceback",
               any(says in p for p in recipe.check_one(d / "c.png")))
    side.write_text(good, encoding="utf-8")

    for i, text in enumerate(("a\x85b\nc", "a\u2028b\nc", "a\rb\nc")):
        dest = d / f"nel-{i}.png"
        check(f"capture with a YAML line-break character {i}",
              cap("--to", str(dest), "--generator", "codex", "--prompt", text), 0)
        doc = yaml.safe_load(recipe.sidecar_of(dest).read_text(encoding="utf-8"))
        check(f"the prompt with that character {i} survives exactly", doc["prompt"], text)


def tags_of(raw: bytes) -> set[str]:
    out, i = set(), 8
    while i + 8 <= len(raw):
        size, tag = struct.unpack(">I4s", raw[i:i + 8])
        out.add(tag.decode("latin-1"))
        i += 12 + size
        if tag == b"IEND":
            break
    return out


def webp_tags(raw: bytes) -> set[bytes]:
    out, i = set(), 12
    while i + 8 <= len(raw):
        tag = raw[i:i + 4]
        size = struct.unpack("<I", raw[i + 4:i + 8])[0]
        out.add(tag)
        i += 8 + size + (size & 1)
    return out


def test_strip(tmp: Path) -> None:
    f = tmp / "s.png"

    keep = (srgb_chunk() + trns_chunk() + raw_chunk(b"pHYs", b"\x00" * 9))
    junk = (raw_chunk(b"tEXt", b"parameters\x00a prompt nobody meant to publish")
            + raw_chunk(b"iTXt", b"XML:com.adobe.xmp\x00\x00\x00\x00\x00<x/>")
            + raw_chunk(b"tIME", b"\x07\xea\x01\x01\x01\x01\x01")
            + raw_chunk(b"eXIf", exif(None)))
    f.write_bytes(png(16, 16, colour=3, extra=keep + junk))
    out, dropped, _ = strip.strip(f, Opt())
    tags = tags_of(out)
    for gone in ("tEXt", "iTXt", "tIME", "eXIf"):
        truthy(f"png {gone} is removed", gone not in tags)
    for stays in ("IHDR", "PLTE", "IDAT", "IEND", "sRGB", "tRNS", "pHYs"):
        truthy(f"png {stays} stays", stays in tags)
    truthy("the embedded prompt is gone", b"nobody meant to publish" not in out)
    check("every removal is reported", len(dropped), 4)

    check("pixel data is untouched",
          [c for c in tags_of(f.read_bytes()) if c == "IDAT"], ["IDAT"])
    truthy("the result is smaller", len(out) < f.stat().st_size)

    out, _, _ = strip.strip(f, Opt(drop_profile=True))
    truthy("--drop-profile removes sRGB", "sRGB" not in tags_of(out))

    # content credentials are a project decision, so they survive by default
    f.write_bytes(png(16, 16, extra=raw_chunk(b"caBX", b"\x00" * 16)))
    truthy("caBX stays by default", "caBX" in tags_of(strip.strip(f, Opt())[0]))
    truthy("caBX goes when asked",
           "caBX" not in tags_of(strip.strip(f, Opt(drop_credentials=True))[0]))

    # an Exif block may or may not carry its own prefix, and a review found the
    # WebP path prepending a second one — no TIFF header, no orientation, a
    # sideways picture stripped in silence. Every container, both conventions.
    for label, wrap in (("bare TIFF", lambda b: b),
                        ("prefixed", lambda b: b"Exif\x00\x00" + b)):
        f.write_bytes(png(16, 16, extra=raw_chunk(b"eXIf", wrap(exif(6)))))
        truthy(f"png refuses a sideways {label} block",
               refuses(f, Opt(), "orientation is 6"))
        w6 = tmp / "o.webp"
        w6.write_bytes(webp_with(300, 200, 0x08, [
            (b"EXIF", wrap(exif(6))),
            (b"VP8L", b"\x2f" + struct.pack("<I", 299 | (199 << 14)))]))
        truthy(f"webp refuses a sideways {label} block",
               refuses(w6, Opt(), "orientation is 6"))
    j6 = tmp / "o.jpg"
    j6.write_bytes(jpeg_with(64, 32, [(0xE1, b"Exif\x00\x00" + exif(3))]))
    truthy("jpeg refuses a sideways block", refuses(j6, Opt(), "orientation is 3"))

    # an orientation that is not upright stops the run rather than rotating it
    f.write_bytes(png(16, 16, extra=raw_chunk(b"eXIf", exif(6))))
    try:
        strip.strip(f, Opt())
        failures.append("  a sideways orientation was stripped silently")
    except strip.Refused as e:
        truthy("the refusal says which orientation", "6" in str(e))
    truthy("--orientation-is-applied is how a person overrides it",
           "eXIf" not in tags_of(strip.strip(f, Opt(orientation_is_applied=True))[0]))
    f.write_bytes(png(16, 16, extra=raw_chunk(b"eXIf", exif(1))))
    truthy("an upright orientation needs no override",
           "eXIf" not in tags_of(strip.strip(f, Opt())[0]))

    # jpeg
    j = tmp / "s.jpg"
    j.write_bytes(jpeg_with(64, 32, [
        (0xE0, b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"),
        (0xE1, b"Exif\x00\x00" + exif(None)),
        (0xE1, b"http://ns.adobe.com/xap/1.0/\x00<x/>"),
        (0xE2, b"ICC_PROFILE\x00\x01\x01" + b"\x00" * 8),
        # JPEG XT framing (CI, En, Z), then the JUMBF superbox header
        (0xEB, b"JP\x00\x01\x00\x00\x00\x01" + struct.pack(">I", 24) + b"jumb"
         + b"c2pa" + b"\x00" * 12),
        (0xEE, b"Adobe\x00\x64\x00\x00\x00\x00\x00"),
        (0xFE, b"a comment"),
    ]))
    out, dropped, _ = strip.strip(j, Opt())
    truthy("jpeg Exif goes", b"Exif\x00\x00" not in out)
    truthy("jpeg XMP goes", b"ns.adobe.com/xap" not in out)
    truthy("jpeg comment goes", b"a comment" not in out)
    truthy("jpeg ICC stays", b"ICC_PROFILE\x00" in out)
    truthy("jpeg JFIF stays", b"JFIF\x00" in out)
    truthy("jpeg Adobe transform stays", b"Adobe\x00" in out)
    truthy("jpeg credentials stay by default", b"c2pa" in out)
    truthy("jpeg credentials go when asked",
           b"c2pa" not in strip.strip(j, Opt(drop_credentials=True))[0])
    truthy("the entropy-coded data is copied verbatim", out.endswith(b"ENTROPY\xff\xd9"))

    # the standard allows 0xFF fill before a marker, and standalone markers carry
    # no length. Reading two bytes of "length" off one walks the parser into the
    # middle of a segment; a review found both parsers doing it.
    for fill in (0, 1, 3):
        for extra in (b"", b"\xff\x01"):      # nothing, then a TEM marker
            j2 = tmp / "fill.jpg"
            j2.write_bytes(jpeg_with(64, 32, [
                (0xE1, b"Exif\x00\x00" + exif(None)),
                (0xE2, b"ICC_PROFILE\x00\x01\x01" + b"\x00" * 8),
            ], pad=b"\xff" * fill + extra))
            label = f"fill={fill} standalone={bool(extra)}"
            got = imgfacts.probe(j2)
            check(f"imgfacts reads it ({label})", got["size"], "64x32")
            stripped, _, _ = strip.strip(j2, Opt())
            truthy(f"strip removes Exif ({label})", b"Exif\x00\x00" not in stripped)
            truthy(f"strip keeps ICC ({label})", b"ICC_PROFILE\x00" in stripped)
            if extra:
                truthy(f"a standalone marker is copied, not dropped ({label})",
                       extra in stripped)
            truthy(f"entropy data survives ({label})",
                   stripped.endswith(b"ENTROPY\xff\xd9"))

    # webp: the chunks go and VP8X must stop advertising them
    w = tmp / "s.webp"
    w.write_bytes(webp_with(300, 200, 0x20 | 0x08 | 0x04, [
        (b"ICCP", b"\x00" * 8),
        (b"EXIF", exif(None)),
        (b"XMP ", b"<x/>"),
        (b"VP8L", b"\x2f" + struct.pack("<I", 299 | (199 << 14))),
    ]))
    out, _, _ = strip.strip(w, Opt())
    tags = webp_tags(out)
    truthy("webp EXIF goes", b"EXIF" not in tags)
    truthy("webp XMP goes", b"XMP " not in tags)
    truthy("webp ICCP stays", b"ICCP" in tags)
    check("the RIFF size is corrected", struct.unpack("<I", out[4:8])[0], len(out) - 8)
    flags = out[20]
    check("the VP8X Exif flag is cleared", flags & strip.VP8X_EXIF, 0)
    check("the VP8X XMP flag is cleared", flags & strip.VP8X_XMP, 0)
    check("the VP8X ICC flag is kept", flags & 0x20, 0x20)

    # a format it does not handle is refused, not half-done
    g = tmp / "s.gif"
    g.write_bytes(gif(16, 16))
    try:
        strip.strip(g, Opt())
        failures.append("  a GIF was processed by a handler that does not exist")
    except strip.Refused:
        pass

    # and the tool checks its own output rather than trusting the operation
    keeping = strip.PNG_RENDER
    try:
        strip.PNG_RENDER = set()               # a policy that drops tRNS
        f.write_bytes(png(16, 16, colour=3, extra=trns_chunk()))
        strip.strip(f, Opt())
        failures.append("  stripping dropped the alpha channel and said nothing")
    except strip.Refused as e:
        truthy("the guard names what changed", "alpha" in str(e))
    finally:
        strip.PNG_RENDER = keeping


def test_no_writes_while_reporting(tmp: Path) -> None:
    """A run with neither --out nor --in-place is a report, and reports do not
    write. An earlier version put a `.stripcheck` file beside the input, which
    also made the report fail outright on a read-only directory."""
    f = tmp / "ro.png"
    f.write_bytes(png(16, 16, extra=raw_chunk(b"tEXt", b"k\x00v")))
    seen = []
    real = strip._write_atomically

    def spy(dest, data, **kw):
        seen.append(str(dest))
        return real(dest, data, **kw)

    strip._write_atomically = spy
    listing = sorted(tmp.iterdir())
    try:
        check("reporting exits 0", strip.main([str(f)]), 0)
        check("reporting writes nothing", seen, [])
        check("reporting leaves the directory as it was", sorted(tmp.iterdir()), listing)
        check("--out writes exactly one file",
              strip.main([str(f), "--out", str(tmp / "sub" / "o.png")]), 0)
        check("and that file is the destination", seen, [str(tmp / "sub" / "o.png")])
        check("and leaves no temporary file beside it",
              sorted(x.name for x in (tmp / "sub").iterdir()), ["o.png"])
    finally:
        strip._write_atomically = real
    truthy("the destination is a real image",
           imgfacts.probe(tmp / "sub" / "o.png")["size"] == "16x16")

    check("--out refuses to combine with --in-place",
          exits(lambda: strip.main([str(f), "--out", str(tmp / "x.png"),
                                    "--in-place"])), 2)
    check("--out refuses more than one input",
          exits(lambda: strip.main([str(f), str(f), "--out", str(tmp / "x.png")])), 2)

    before = f.read_bytes()
    check("--in-place exits 0", strip.main([str(f), "--in-place"]), 0)
    after = f.read_bytes()
    truthy("--in-place actually rewrote the file", after != before)
    truthy("and removed the text chunk", b"tEXt" not in after)
    check("--in-place is idempotent", strip.main([str(f), "--in-place"]), 0)
    check("nothing left to remove the second time", f.read_bytes(), after)
    check("an unreadable file exits 1", strip.main([str(tmp / "junk.png")]), 1)

    # --in-place on a symlink strips the file it points to and keeps the link
    real = tmp / "real.png"
    real.write_bytes(png(16, 16, extra=raw_chunk(b"tEXt", b"k\x00v")))
    link = tmp / "link.png"
    link.symlink_to(real)
    check("--in-place through a symlink exits 0", strip.main([str(link), "--in-place"]), 0)
    truthy("the link is still a link", link.is_symlink())
    truthy("and the file it points to was stripped", b"tEXt" not in real.read_bytes())


def test_malformed_input(tmp: Path) -> None:
    """Cut-short and odd files. Each case here was a traceback or a confident
    wrong answer before a review built the bytes and ran them."""
    def unreadable(name: str, raw: bytes) -> None:
        truthy(f"{name} is Unreadable, not a crash or an answer",
               raises(lambda: imgfacts.probe_bytes(raw), imgfacts.Unreadable))

    sof = b"\xff\xd8\xff\xc0\x00\x04\x08\x00"
    unreadable("a JPEG frame header too short to hold a size", sof)
    unreadable("a GIF shorter than its screen descriptor", b"GIF89a\x10\x00")
    vp8x = webp_vp8x(16, 16, alpha=False, icc=False)
    unreadable("a VP8X header cut short", vp8x[:21])
    vp8l = webp_vp8l(16, 16, alpha=False)
    unreadable("a VP8L chunk with no data", vp8l[:20])
    unreadable("a VP8L chunk with no signature byte", vp8l[:20] + b"\x00" + vp8l[21:])
    f = tmp / "cut.webp"
    f.write_bytes(vp8x[:21])
    check("imgfacts exits 1 on a cut-short file, without a traceback",
          imgfacts.main([str(f)]), 1)
    check("strip exits 1 on it too", strip.main([str(f)]), 1)

    for frame, note in ((0xC0, "baseline"), (0xC1, "sequential"),
                        (0xCE, "progressive"), (0xC3, "lossless")):
        body = b"\x08" + struct.pack(">HH", 8, 8) + b"\x01\x01\x11\x00"
        raw = (b"\xff\xd8" + bytes([0xFF, frame]) + struct.pack(">H", len(body) + 2)
               + body + b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00")
        truthy(f"SOF {frame:#x} is labelled {note}",
               note in imgfacts.probe_bytes(raw)["notes"])

    # A graphic control extension is in every animated GIF, for the delay; only
    # its transparency bit says alpha. The colour table holds the extension's
    # introducer by chance, which a byte search mistook for one.
    head = (b"GIF89a" + struct.pack("<HH", 4, 4) + b"\x80\x00\x00"
            + b"\x21\xf9\x04\x01\x21\xf9")
    frame = b"\x2c" + b"\x00" * 8 + b"\x00" + b"\x02\x02\x4c\x01\x00"
    gce = lambda flags: b"\x21\xf9\x04" + bytes([flags]) + b"\x00\x00\x00\x00"
    check("a GIF whose extension sets no transparency has no alpha",
          imgfacts.probe_bytes(head + gce(0) + frame + b"\x3b")["alpha"], False)
    check("one that sets it has alpha",
          imgfacts.probe_bytes(head + gce(1) + frame + b"\x3b")["alpha"], True)
    check("and a later frame setting it counts",
          imgfacts.probe_bytes(head + frame + gce(1) + frame + b"\x3b")["alpha"], True)

    for size in ("16x0", "0x16", "-16x16"):
        check(f"--check-size {size} is not a size",
              imgfacts.main([f"--check-size={size}"]), 2)
    for aspect in ("0:1", "1:0", "0:0"):
        check(f"--check-aspect {aspect} is not an aspect",
              imgfacts.main([f"--check-aspect={aspect}"]), 2)
    for w, h in ((16, 16), (100000, 100000), (64, 32)):
        n = imgfacts.nearest_legal(w, h)
        truthy(f"nearest_legal({w},{h}) answers however far off the request is", n)
        if n:
            check(f"nearest_legal({w},{h}) is legal", imgfacts.illegal(*n), set())
            check(f"nearest_legal({w},{h}) keeps the shape",
                  imgfacts.aspect_of(*n), imgfacts.aspect_of(w, h))


def test_strip_leaks(tmp: Path) -> None:
    """What a stripper must not let through, and what it must not take away."""
    f = tmp / "leak.jpg"
    second = jpeg_with(8, 8, [(0xE1, b"Exif\x00\x00" + exif(None) + b"GPSSECRET")])
    f.write_bytes(jpeg_with(16, 16, []) + second)
    out, dropped, _ = strip.strip(f, Opt())
    truthy("an appended second JPEG and its Exif are gone", b"GPSSECRET" not in out)
    truthy("and the removal is reported", any("after EOI" in d for d in dropped))
    truthy("the image itself still ends at EOI", out.endswith(b"\xff\xd9"))

    # A progressive file puts segments between its scans; the policy applies
    # there too, and the scans themselves survive byte for byte.
    scan = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
    entropy = b"AB\xff\x00CD\xff\xd0EF"            # a stuffed byte and a restart
    com = b"\xff\xfe" + struct.pack(">H", 2 + 6) + b"SECRET"
    dht = b"\xff\xc4" + struct.pack(">H", 2 + 3) + b"\x00\x01\x02"
    raw = jpeg_with(16, 16, [])[:-2] + dht + com + scan + entropy + b"\xff\xd9"
    f.write_bytes(raw)
    out, dropped, _ = strip.strip(f, Opt())
    truthy("a comment between scans is removed", b"SECRET" not in out)
    truthy("a table between scans stays", dht in out)
    truthy("entropy data with stuffing and restarts survives intact",
           entropy in out and out.count(scan) == 2)

    thumb = (0xE0, b"JFXX\x00\x10" + b"THUMBNAILDATA")
    jfif = (0xE0, b"JFIF\x00\x01\x02\x00\x00\x01\x00\x01\x00\x00")
    f.write_bytes(jpeg_with(16, 16, [jfif, thumb]))
    out, _, _ = strip.strip(f, Opt())
    truthy("a JFXX thumbnail in APP0 is removed", b"THUMBNAILDATA" not in out)
    truthy("the JFIF APP0 stays", b"JFIF\x00" in out)

    f = tmp / "hdr.png"
    f.write_bytes(png(16, 16, extra=raw_chunk(b"cICP", b"\x09\x10\x00\x01")
                      + raw_chunk(b"cLLI", b"\x00" * 8)))
    out, _, before = strip.strip(f, Opt())
    truthy("cICP stays: it is the colour space", "cICP" in tags_of(out))
    truthy("cLLI stays with it", "cLLI" in tags_of(out))
    check("imgfacts reports cICP", before["colour"], "cICP declared")

    f = tmp / "cut.png"
    whole = png(16, 16, extra=raw_chunk(b"tEXt", b"k\x00v"))
    f.write_bytes(whole[:-30])
    truthy("a truncated PNG is refused, not written short",
           refuses(f, Opt(), "truncated"))
    f.write_bytes(whole[:-12])
    truthy("a PNG with no IEND is refused", refuses(f, Opt(), "IEND"))
    f = tmp / "cut.webp"
    full = webp_with(16, 16, 0, [(b"EXIF", exif(None) * 4)])
    f.write_bytes(full[:-6])
    truthy("a truncated WebP is refused", refuses(f, Opt(), "truncated"))
    whole_webp = webp_with(16, 16, 0, [(b"VP8L", b"\x2f" + bytes(4))])
    check("a whole WebP is complete", imgfacts.complete(whole_webp), True)
    check("a VP8X canvas with no image chunk after it is not",
          imgfacts.complete(webp_vp8x(16, 16, False, False)), False)
    check("a lossless WebP with its pixels is", imgfacts.complete(webp_vp8l(16, 16, False)), True)
    check("a VP8X canvas whose image chunk is empty is not",
          imgfacts.complete(webp_with(16, 16, 0, [(b"VP8 ", b"")])), False)
    no_idat = png(16, 16)
    at = no_idat.index(b"IDAT") - 4
    no_idat = no_idat[:at] + no_idat[at + 12 + struct.unpack(">I", no_idat[at:at + 4])[0]:]
    check("a PNG whose IEND follows its header with no IDAT is not",
          imgfacts.complete(no_idat), False)
    jpg = jpeg_with(8, 8, [])
    check("a JPEG with a scan reaches EOI", imgfacts.complete(jpg), True)
    check("one whose EOI follows its header with no scan does not",
          imgfacts.complete(jpg[:jpg.index(b"\xff\xda")] + b"\xff\xd9"), False)
    check("a GIF whose trailer follows its header with no image is not complete",
          imgfacts.complete(gif(2, 2) + b"\x3b"), False)
    frame = bytes(16)                                  # ANMF's own frame header
    lossless = b"VP8L" + struct.pack("<I", 5) + b"\x2f" + bytes(4) + b"\x00"
    check("an ANMF frame holding a bitstream is pixels",
          imgfacts.complete(webp_with(16, 16, 0x02, [(b"ANMF", frame + lossless)])), True)
    check("a VP8L chunk without its 0x2f signature is not pixels",
          imgfacts.complete(webp_with(16, 16, 0, [(b"VP8L", bytes(5))])), False)
    check("nor a VP8 chunk without its frame start code",
          imgfacts.complete(webp_with(16, 16, 0, [(b"VP8 ", bytes(10))])), False)
    check("an ANMF whose nested odd chunk lacks its own pad byte is not",
          imgfacts.complete(webp_with(16, 16, 0x02, [(b"ANMF", frame + lossless[:-1])])),
          False)
    check("an ANMF frame whose nested chunk is empty is not",
          imgfacts.complete(webp_with(16, 16, 0x02,
                                      [(b"ANMF", frame + b"VP8L" + bytes(4))])), False)
    odd = webp_with(16, 16, 0, [(b"VP8L", b"\x2f" + bytes(4))])     # 5 bytes: padded
    cut = odd[:-1]
    check("one cut at the pad byte its odd last chunk needs is not",
          imgfacts.complete(cut[:4] + struct.pack("<I", len(cut) - 8) + cut[8:]), False)
    check("one whose RIFF size is still zero is not",
          imgfacts.complete(whole_webp[:4] + b"\0\0\0\0" + whole_webp[8:]), False)


# --- engine, refute, render -------------------------------------------------

FAKE = """#!/usr/bin/env python3
import json, os, subprocess, sys
argv = sys.argv[1:]
prompt = sys.stdin.read()
with open(os.environ["FAKE_LOG"], "a") as log:
    log.write(json.dumps({"argv": argv, "stdin": prompt}) + "\\n")
me = os.path.basename(sys.argv[0])
only = os.environ.get("FAKE_ONLY")
if only and me not in only.split(","):
    sys.exit(1)                                    # this engine is unreachable
if os.environ.get("FAKE_SPAWN"):                   # a tree that outlives a kill of
    p = subprocess.Popen(["sleep", "30"])          # the direct child alone
    open(os.environ["FAKE_SPAWN"], "w").write(str(p.pid))
    import time; time.sleep(30)
answer = os.environ["FAKE_ANSWER"]
if os.environ.get("FAKE_STDERR_BYTES"):            # a log that is not UTF-8
    sys.stderr.buffer.write(b"progress \\xff\\xfe\\n"); sys.stderr.flush()
if "-o" in argv:                                   # codex writes a file
    with open(argv[argv.index("-o") + 1], "wb") as f:
        f.write(answer.encode() + (b"\\xff" if os.environ.get("FAKE_BYTES") else b""))
else:                                              # claude and agy print an envelope
    envelope = {"type": "result", "structured_output": json.loads(answer)}
    if os.environ.get("FAKE_IS_ERROR"):
        envelope.update(subtype="error_during_execution", is_error=True)
    sys.stdout.flush()
    sys.stdout.buffer.write(json.dumps(envelope).encode()
                            + (b"\\xff" if os.environ.get("FAKE_BYTES") else b"") + b"\\n")
    sys.stdout.flush()
    noise = os.environ.get("FAKE_NOISE")
    if noise:
        print(noise)                               # a log line after the answer
sys.exit(int(os.environ.get("FAKE_RC", "0")))
"""


@contextlib.contextmanager
def fake_engines(tmp: Path, answer):
    import os
    bin_dir = tmp / "fakebin"
    bin_dir.mkdir(exist_ok=True)
    for name in engine.ENGINES["runs_on"]:
        f = bin_dir / name
        f.write_text(FAKE, encoding="utf-8")
        f.chmod(0o755)
    log = tmp / "fake.log"
    log.write_text("", encoding="utf-8")
    saved = {k: os.environ.get(k) for k in ("PATH", "FAKE_LOG", "FAKE_ANSWER")}
    os.environ.update(PATH=f"{bin_dir}{os.pathsep}{saved['PATH']}",
                      FAKE_LOG=str(log), FAKE_ANSWER=json.dumps(answer))
    try:
        yield log
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_engine(tmp: Path) -> None:
    """A checker that answered outside its schema did not answer."""
    good = {"refuted": False, "reason": "r", "what_would_settle_it": "w"}
    for name in engine.ENGINES["runs_on"]:
        with fake_engines(tmp, good):
            check(f"{name}: a conforming answer comes back",
                  engine.run(name, "-starts with a dash", refute.SCHEMA), good)
        with fake_engines(tmp, dict(good, refuted="false")):
            truthy(f"{name}: the string 'false' is not a boolean",
                   raises(lambda: engine.run(name, "p", refute.SCHEMA), engine.EngineError))
        with fake_engines(tmp, {"reason": "r"}):
            truthy(f"{name}: a missing required key is an error, not a KeyError",
                   raises(lambda: engine.run(name, "p", refute.SCHEMA), engine.EngineError))
        with fake_engines(tmp, None):
            truthy(f"{name}: a null answer is an error, not a TypeError",
                   raises(lambda: engine.run(name, "p", refute.SCHEMA), engine.EngineError))
    with fake_engines(tmp, good) as log:
        engine.run("codex", "-p --help", refute.SCHEMA)
        engine.run("claude", "-p --help", refute.SCHEMA)
        calls = [json.loads(x) for x in log.read_text().splitlines()]
        check("codex and claude receive the prompt on stdin, verbatim",
              [c["stdin"] for c in calls], ["-p --help", "-p --help"])
        truthy("and never as an argument", all("-p --help" not in c["argv"] for c in calls))

    nested = {"type": "object", "properties": {
        "a": {"anyOf": [{"type": "object", "properties": {"x": {"type": "string"}}},
                        {"type": "null"}]},
        "b": {"type": ["object", "null"], "properties": {"y": {"type": "integer"}}},
        "c": {"type": "array", "items": [{"type": "object", "properties": {}}]}}}
    closed = engine.strict(nested)
    check("strict closes an object inside anyOf",
          closed["properties"]["a"]["anyOf"][0]["additionalProperties"], False)
    check("strict closes a nullable object", closed["properties"]["b"]["additionalProperties"], False)
    check("strict closes list-form items", closed["properties"]["c"]["items"][0]["additionalProperties"], False)
    check("strict requires every property", closed["required"], ["a", "b", "c"])

    check("engine.py with no --running stops rather than running anything",
          exits(lambda: engine.main(["codex", "--prompt-file", "p", "--schema", "s"])), 2)

    claims = tmp / "claims.json"
    claims.write_text(json.dumps([{"id": "c1", "claim": "the file is 1536x1024"}]))
    with fake_engines(tmp, good):
        check("refute exits 0 when every claim was read", refute.main(["--running", "claude", str(claims)]), 0)
    with fake_engines(tmp, None):
        check("refute exits 1 when a claim went unchecked",
              refute.main(["--running", "claude", str(claims)]), 1)
        check("and with --json too",
              refute.main(["--running", "claude", "--json", str(claims)]), 1)
    for bad in ("[]", '[{"id": "x"}]', '["text"]', "not json"):
        claims.write_text(bad)
        check(f"refute rejects the claims file {bad!r} before asking anyone",
              refute.main(["--running", "claude", str(claims)]), 2)

    skill = tmp / "SKILL.md"
    key = next(iter(render.H["delivered"]))
    skill.write_text(f"# x\n\n<!-- deliver:{key} -->\nold\n", encoding="utf-8")
    truthy("render refuses an open marker with no close, rather than duplicating",
           raises(lambda: render.render(skill), SystemExit))
    check("and leaves the file as it was", skill.read_text(encoding="utf-8"),
          f"# x\n\n<!-- deliver:{key} -->\nold\n")


def test_precommit_hook(tmp: Path) -> None:
    """The hook judges the commit, which is the index — not the working tree.

    Validating the tree failed a clean commit because of an unrelated,
    unstaged half-edit, and would pass a broken staged file whose fix sat
    unstaged beside it."""
    import os
    import shutil
    import subprocess
    if shutil.which("git") is None:
        failures.append("  git is not on PATH; the pre-commit hook was not exercised")
        return
    repo = tmp / "hookrepo"
    root = Path(__file__).resolve().parent.parent
    shutil.copytree(root, repo, symlinks=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__"))
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(repo), *args], env=env,
                              capture_output=True, text=True)

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "--no-verify", "-m", "base")
    hook = repo / "image-tools" / "githooks" / "pre-commit"

    def hook_passes() -> bool:
        return subprocess.run(["sh", str(hook)], cwd=repo, env=env,
                              capture_output=True, text=True).returncode == 0

    target = repo / "skills" / "image-prompt" / "playbooks" / "structure.md"
    good = target.read_text(encoding="utf-8")
    broken = good + "\n#" + "TODO(agent): no class here\n"
    check("the hook passes a clean index", hook_passes(), True)
    target.write_text(broken, encoding="utf-8")
    check("an unstaged breakage does not fail the commit", hook_passes(), True)
    git("add", str(target))
    target.write_text(good, encoding="utf-8")
    check("a staged breakage fails the commit, whatever the tree says",
          hook_passes(), False)
    git("reset", "-q", "--hard")
    # A sparse checkout leaves files out of the tree, not out of the commit.
    git("sparse-checkout", "set", "--no-cone", "/*", "!/docs/")
    check("a sparse checkout does not fail the commit over files it left out",
          hook_passes(), True)


def test_strip_writes(tmp: Path) -> None:
    """How a stripped file reaches the disk. Each case is a regression a review
    found in the atomic write: a new inode is right for a lone file and wrong
    for one with other names, and a write that fails is that file's failure,
    not a traceback that abandons the rest of the run."""
    import os
    d = tmp / "writes"
    d.mkdir()
    junk = raw_chunk(b"tEXt", b"k\x00v")

    h1, h2 = d / "h1.png", d / "h2.png"
    h1.write_bytes(png(16, 16, extra=junk))
    os.link(h1, h2)
    check("--in-place on a hard-linked file exits 0", strip.main([str(h1), "--in-place"]), 0)
    truthy("every name of a hard-linked file sees the stripped bytes",
           b"tEXt" not in h2.read_bytes())
    check("and the names still share one file", h1.stat().st_ino, h2.stat().st_ino)

    ro = d / "ro"
    ro.mkdir()
    f = ro / "a.png"
    f.write_bytes(png(16, 16, extra=junk))
    real_access = strip.os.access
    strip.os.access = lambda path, mode, *a, **k: (
        False if Path(path) == ro and mode == os.W_OK else real_access(path, mode, *a, **k))
    inode = f.stat().st_ino
    try:
        check("--in-place in a directory it cannot create files in exits 0",
              strip.main([str(f), "--in-place"]), 0)
    finally:
        strip.os.access = real_access
    check("and it wrote through the same inode, the only way open to it",
          f.stat().st_ino, inode)
    truthy("and the file was stripped through its own inode", b"tEXt" not in f.read_bytes())

    # Writing through an inode cannot be atomic, so a failure part-way must
    # put the original back; if even that fails, the original is kept
    # somewhere the error names. A half-written only copy is never the result.
    hl, hl2 = d / "fail1.png", d / "fail2.png"
    original = png(16, 16, extra=junk)
    hl.write_bytes(original)
    os.link(hl, hl2)
    real_fsync, calls = strip.os.fsync, []
    target = hl.stat().st_ino

    def failing_fsync(fd):                     # only the image's own inode fails;
        if os.fstat(fd).st_ino == target:      # the recovery copy is elsewhere
            calls.append(fd)
            if len(calls) == 1:
                raise OSError(28, "No space left on device")
        return real_fsync(fd)

    strip.os.fsync = failing_fsync
    try:
        check("a write through the inode that fails exits 1",
              strip.main([str(hl), "--in-place"]), 1)
    finally:
        strip.os.fsync = real_fsync
    check("and the original is back, for every name", hl2.read_bytes(), original)

    strip.os.fsync = lambda fd: (real_fsync(fd) if os.fstat(fd).st_ino != target
                                 else (_ for _ in ()).throw(OSError(5, "I/O error")))
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            check("a failed restore also exits 1", strip.main([str(hl), "--in-place"]), 1)
    finally:
        strip.os.fsync = real_fsync
    import re as _re
    saved = _re.search(r"original saved to (\S+)", err.getvalue())
    truthy("and the error names where the original was saved", saved)
    if saved:
        check("which holds the original bytes", Path(saved.group(1)).read_bytes(), original)
        Path(saved.group(1)).unlink()

    # The recovery copy exists before the inode is touched: if it cannot be
    # made, nothing is changed, rather than finding out after the damage.
    real_mkstemp = strip.tempfile.mkstemp
    strip.tempfile.mkstemp = lambda *a, **k: (_ for _ in ()).throw(OSError(28, "No space"))
    before_bytes = hl.read_bytes()
    try:
        check("no room for a recovery copy refuses the write-through",
              strip.main([str(hl), "--in-place"]), 1)
    finally:
        strip.tempfile.mkstemp = real_mkstemp
    check("and leaves the file exactly as it was", hl.read_bytes(), before_bytes)
    import glob as _glob
    pattern = str(Path(tempfile.gettempdir()) / f"{hl.name}.original.*")
    already = set(_glob.glob(pattern))
    check("a successful write-through leaves no recovery copy behind",
          (strip.main([str(hl), "--in-place"]), set(_glob.glob(pattern)) - already),
          (0, set()))

    # Every way out except a failed restore removes the recovery copy: a run
    # that carries on to the next file must not strand originals in /tmp.
    def strays() -> set:
        return set(_glob.glob(pattern))
    hl.write_bytes(png(16, 16, extra=junk))
    already = strays()
    real_open = strip.__dict__.get("open", open)
    strip.open = lambda path, *a, **k: (
        (_ for _ in ()).throw(PermissionError(13, "denied")) if Path(path) == hl.resolve()
        else real_open(path, *a, **k))
    try:
        check("an image that cannot be opened for writing exits 1",
              strip.main([str(hl), "--in-place"]), 1)
    finally:
        del strip.open
    check("and leaves no recovery copy behind", strays() - already, set())
    strip.os.fsync = lambda fd: (real_fsync(fd) if os.fstat(fd).st_ino == target
                                 else (_ for _ in ()).throw(OSError(28, "No space")))
    try:
        check("a recovery copy that cannot be finished refuses the write",
              strip.main([str(hl), "--in-place"]), 1)
    finally:
        strip.os.fsync = real_fsync
    check("and leaves no partial copy behind", strays() - already, set())
    truthy("and the image was not touched", b"tEXt" in hl.read_bytes())

    # An interrupt mid-write is a failure like any other: the original goes
    # back before the interrupt carries on, and nothing is stranded.
    hl.write_bytes(png(16, 16, extra=junk))
    pristine = hl.read_bytes()
    real_overwrite, seen = strip._overwrite, []

    def interrupted(f, data):
        seen.append(1)
        if len(seen) == 1:
            f.seek(0)
            f.write(data[:10])                       # half a write, then Ctrl-C
            raise KeyboardInterrupt
        return real_overwrite(f, data)

    strip._overwrite = interrupted
    try:
        truthy("an interrupt mid-write still propagates",
               raises(lambda: strip._write_atomically(hl, b"x" * 20), KeyboardInterrupt))
    finally:
        strip._overwrite = real_overwrite
    check("and the original is back first", hl.read_bytes(), pristine)
    check("and no recovery copy is stranded", strays() - already, set())

    # Interrupted, and the restore fails too: the interrupt is still what
    # propagates, and the copy's location is said before it does.
    def always(f, data):
        f.seek(0)
        f.write(data[:10])
        raise KeyboardInterrupt if data != pristine else OSError(5, "I/O error")

    strip._overwrite = always
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            truthy("the original interrupt propagates, not the restore's error",
                   raises(lambda: strip._write_atomically(hl, b"x" * 20), KeyboardInterrupt))
    finally:
        strip._overwrite = real_overwrite
    kept = _re.search(r"original saved to (\S+)", err.getvalue())
    truthy("and the copy's location is said before it does", kept)
    if kept:
        check("and that copy is the original", Path(kept.group(1)).read_bytes(), pristine)
        Path(kept.group(1)).unlink()

    # The restore works and the interrupt is in flight; a cleanup that then
    # fails must not replace it with an error main() would continue past.
    hl.write_bytes(pristine)

    def interrupted_once(f, data):
        if data != pristine:
            f.seek(0)
            f.write(data[:10])
            raise KeyboardInterrupt
        return real_overwrite(f, data)

    real_unlink = Path.unlink
    Path.unlink = lambda self, *a, **k: (_ for _ in ()).throw(OSError(5, "I/O error")) \
        if ".original." in self.name else real_unlink(self, *a, **k)
    strip._overwrite = interrupted_once
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            truthy("a failed cleanup does not swallow the interrupt",
                   raises(lambda: strip.main([str(hl), "--in-place"]), KeyboardInterrupt))
    finally:
        strip._overwrite = real_overwrite
        Path.unlink = real_unlink
    for stray in strays() - already:
        Path(stray).unlink()

    # A failed write, then Ctrl-C during the restore: the interrupt is not
    # converted into an error that main() would report and continue past.
    hl.write_bytes(pristine)

    def write_fails_then_interrupted(f, data):
        f.seek(0)
        f.write(data[:10])
        raise OSError(28, "No space") if data != pristine else KeyboardInterrupt

    strip._overwrite = write_fails_then_interrupted
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            truthy("an interrupt during the restore stays an interrupt",
                   raises(lambda: strip.main([str(hl), "--in-place"]), KeyboardInterrupt))
    finally:
        strip._overwrite = real_overwrite
    kept = _re.search(r"original saved to (\S+)", err.getvalue())
    truthy("and the copy's location is said first", kept)
    if kept:
        Path(kept.group(1)).unlink()

    blocker = d / "blocker"
    blocker.write_bytes(b"a file, not a directory")
    src = d / "src.png"
    src.write_bytes(png(16, 16, extra=junk))
    check("a write that cannot happen is reported and exits 1, not a traceback",
          strip.main([str(src), "--out", str(blocker / "out.png")]), 1)
    check("and a later file in the same run is still processed",
          strip.main([str(blocker / "nope.png"), str(src)]), 1)

    dangling = d / "dl.png"
    dangling.symlink_to(d / "made" / "here.png")
    check("--out through a dangling link creates the link's target",
          strip.main([str(src), "--out", str(dangling)]), 0)
    truthy("the target now exists", (d / "made" / "here.png").exists())

    ending = jpeg_with(16, 16, [])[:-2] + b"\xff\xff"
    truthy("the segment walk stops at fill bytes that run to the end",
           not raises(lambda: list(imgfacts.jpeg_segments(ending, through_scans=True)),
                      IndexError))
    real_strip = strip.strip
    strip.strip = lambda *a, **k: [][0]           # any parser slip of this kind
    try:
        check("a parser IndexError is that file's failure, not a traceback",
              strip.main([str(src)]), 1)
    finally:
        strip.strip = real_strip


def reported_bytes(dropped: list[str]) -> int:
    import re
    return sum(int(m.replace(",", "")) for d in dropped
               for m in re.findall(r"([\d,]+) (?:stray )?bytes", d))


def test_strip_accounts_for_every_byte(tmp: Path) -> None:
    """Every byte that does not reach the output is reported, and a file that is
    cut short is refused — the same rules PNG already followed, now for JPEG
    and WebP. A review found JPEG and WebP bytes going missing under "nothing
    to remove", and truncated JPEGs written out as if whole."""
    f = tmp / "acct.jpg"
    jfif = (0xE0, b"JFIF\x00\x01\x02\x00\x00\x01\x00\x01\x00\x00")
    good = jpeg_with(16, 16, [jfif])
    cut = good.index(b"\xff\xdb") if b"\xff\xdb" in good else good.index(b"\xff\xc0")
    f.write_bytes(good[:cut] + b"JUNK!" + good[cut:])
    out, dropped, _ = strip.strip(f, Opt())
    truthy("stray bytes between segments are reported, not dropped silently",
           any("between segments" in d for d in dropped))

    f.write_bytes(good[:-2])                                  # no EOI
    truthy("a JPEG with no EOI is refused as truncated", refuses(f, Opt(), "EOI"))
    sos_at = good.index(b"\xff\xda")
    f.write_bytes(good[:sos_at + 6])                          # a segment past the end
    truthy("a segment running past the end is refused", refuses(f, Opt(), "truncated"))

    thumb = b"\x02\x02" + b"\x11\x22\x33" * 4
    f.write_bytes(jpeg_with(16, 16, [(0xE0, jfif[1][:-2] + thumb)]))
    out, dropped, _ = strip.strip(f, Opt())
    truthy("a thumbnail inside the JFIF APP0 is removed", b"\x11\x22\x33" not in out)
    truthy("and reported", any("thumbnail" in d for d in dropped))
    truthy("and the JFIF header itself stays", b"JFIF\x00\x01\x02" in out)
    check("the result still reads as the same image",
          imgfacts.probe_bytes(out)["size"], "16x16")

    w = tmp / "acct.webp"
    base = webp_with(16, 16, 0, [])
    w.write_bytes(base + b"JUNKJUNKJUNK")
    out, dropped, _ = strip.strip(w, Opt())
    truthy("data after the RIFF end is reported", any("after RIFF" in d for d in dropped))
    check("and not copied", out, base)
    w.write_bytes(webp_with(16, 16, 0x08, []))                # EXIF flag, no EXIF
    out, dropped, _ = strip.strip(w, Opt())
    truthy("a cleared VP8X flag is reported", any("flag" in d for d in dropped))
    w.write_bytes(webp_with(16, 16, 0x08, [(b"EXIF", exif(None))]))
    out, dropped, _ = strip.strip(w, Opt())
    check("a flag cleared with its chunk is one removal, not two lines",
          [d for d in dropped if "flag" in d], [])
    big = bytearray(webp_with(16, 16, 0, []))
    big[4:8] = struct.pack("<I", len(big) + 100)
    w.write_bytes(bytes(big))
    truthy("a RIFF size past the end of the file is refused as truncated",
           refuses(w, Opt(), "truncated"))

    # An odd final chunk missing its pad ends exactly at the RIFF end; the
    # byte after it belongs to the trailer, and must not ride along as the pad.
    head = (bytes([0]) + b"\x00\x00\x00" + (15).to_bytes(3, "little")
            + (15).to_bytes(3, "little"))
    body = b"WEBP" + b"VP8X" + struct.pack("<I", len(head)) + head \
        + b"ANIM" + struct.pack("<I", 1) + b"\x07"
    w.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body + b"SECRET")
    out, dropped, _ = strip.strip(w, Opt())
    truthy("no trailer byte is copied in as a missing pad", b"S" not in out[-2:])
    check("and the ledger still balances", reported_bytes(dropped), len(w.read_bytes()) - len(out))

    # An unpadded odd final chunk that is dropped counts the bytes it had, not
    # the pad it never had; and a short residue inside the RIFF is reported
    # even when a trailer follows the RIFF end.
    head = (bytes([0]) + b"\x00\x00\x00" + (15).to_bytes(3, "little")
            + (15).to_bytes(3, "little"))
    vp8x = b"VP8X" + struct.pack("<I", len(head)) + head
    body = b"WEBP" + vp8x + b"EXIF" + struct.pack("<I", 1) + b"\x07"
    w.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)
    out, dropped, _ = strip.strip(w, Opt())
    check("an unpadded dropped chunk is counted as the bytes it had",
          reported_bytes(dropped), len(w.read_bytes()) - len(out))
    body = b"WEBP" + vp8x + b"abc"
    w.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body + b"TRAILR")
    out, dropped, _ = strip.strip(w, Opt())
    check("residue inside the RIFF and a trailer after it are both counted",
          reported_bytes(dropped), len(w.read_bytes()) - len(out))

    # And the tool holds itself to that: a handler that under-counts is refused
    # at run time, not shipped under a report that is wrong.
    real = strip.HANDLERS["PNG"]
    strip.HANDLERS["PNG"] = lambda raw, opt: (lambda o, d: (o, [(w, n - 1) for w, n in d]))(*real(raw, opt))
    try:
        f = tmp / "ledger-guard.png"
        f.write_bytes(png(16, 16, extra=raw_chunk(b"tEXt", b"k\x00v")))
        truthy("a report that does not balance is refused", refuses(f, Opt(), "accounts for"))
    finally:
        strip.HANDLERS["PNG"] = real

    # The report is a ledger: what it names adds up to what the file lost.
    for name, raw in (
            ("png", png(16, 16, extra=raw_chunk(b"tEXt", b"k\x00v")
                        + raw_chunk(b"tIME", b"\x07\xea\x01\x01\x01\x01\x01")) + b"TAIL"),
            ("jpg", jpeg_with(16, 16, [(0xE1, b"Exif\x00\x00" + exif(None)),
                                       (0xFE, b"a comment")], pad=b"\xff") + b"after"),
            ("webp", webp_with(16, 16, 0x08, [(b"EXIF", exif(None)), (b"XMP ", b"<x/>")])
             + b"trailer!")):
        f = tmp / f"ledger.{name}"
        f.write_bytes(raw)
        out, dropped, _ = strip.strip(f, Opt())
        check(f"{name}: the bytes the report names are the bytes the file lost",
              reported_bytes(dropped), len(raw) - len(out))


def test_edges_round_four(tmp: Path) -> None:
    """Edges a fourth review found in engine, imgfacts and render."""
    check("engine.py with a missing prompt file exits 2, not a traceback",
          engine.main(["--running", "claude", "codex", "--prompt-file",
                       str(tmp / "nope.txt"), "--schema", str(tmp / "nope.json")]), 2)
    bad = tmp / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    (tmp / "p.txt").write_text("p", encoding="utf-8")
    check("and with a schema that is not JSON",
          engine.main(["--running", "claude", "codex", "--prompt-file",
                       str(tmp / "p.txt"), "--schema", str(bad)]), 2)
    deep = engine.strict({"type": "object", "properties": {},
                          "dependentSchemas": {"a": {"type": "object", "properties": {}}},
                          "propertyNames": {"type": "object"},
                          "additionalItems": {"type": "object"},
                          "unevaluatedProperties": {"type": "object"}})
    truthy("strict still closes objects under every schema keyword",
           all(x.get("additionalProperties") is False for x in (
               deep["dependentSchemas"]["a"], deep["propertyNames"],
               deep["additionalItems"], deep["unevaluatedProperties"])))
    check("1.0 is an integer, as JSON Schema says",
          engine.conforms(1.0, {"type": "integer"}), [])
    truthy("1.5 is not", engine.conforms(1.5, {"type": "integer"}))
    schema = {"type": "object", "properties": {
        "mode": {"type": "string", "default": {"type": "object", "properties": {}}},
        "pick": {"const": {"type": "object"}}}}
    closed = engine.strict(schema)
    check("strict leaves a default that looks like a schema alone",
          closed["properties"]["mode"]["default"], {"type": "object", "properties": {}})
    check("and a const", closed["properties"]["pick"]["const"], {"type": "object"})

    check("a size just past the ratio limit still has a legal neighbour inside "
          "the tolerance", imgfacts.nearest_legal(3010, 1000) is not None, True)
    # The cut-off uses the search's own drift rule, in both orientations: a
    # fixed margin answered None for shapes the search itself would accept.
    for w, h in ((75376, 25000), (1000, 3010)):
        n = imgfacts.nearest_legal(w, h)
        truthy(f"nearest_legal({w},{h}) answers inside the tolerance", n)
        if n:
            check(f"nearest_legal({w},{h}) is legal", imgfacts.illegal(*n), set())
    for w, h in ((3840, 1024), (1024, 3840), (25000, 75376)):
        check(f"nearest_legal({w},{h}) is past the limit by more than the tolerance",
              imgfacts.nearest_legal(w, h), None)

    skill = tmp / "SKILL2.md"
    key = next(iter(render.H["delivered"]))
    skill.write_text(f"<!-- /deliver:{key} -->\nx\n<!-- deliver:{key} -->\n", encoding="utf-8")
    try:
        render.render(skill)
        said = ""
    except SystemExit as e:
        said = str(e)
    truthy("render names markers in the wrong order as such", "order" in said)


def test_recipe_round_five(tmp: Path) -> None:
    """A flag contradicting the directory, recipes capture wrote and check
    refused, an input path cut at its own colon, and one odd entry ending a
    whole check."""
    import os
    d = tmp / "r5"
    home = d / "codex-home"
    out = home / "generated_images" / "s1"
    out.mkdir(parents=True)
    (out / "exec-1.png").write_bytes(png(32, 32))
    aspect_gen = sorted(imgfacts.ASPECT_GENERATORS)[0]
    old = os.environ.get("CODEX_HOME")
    os.environ["CODEX_HOME"] = str(home)
    try:
        check("--generator naming another generator than the directory is refused",
              recipe.main(["capture", "--from", str(out / "exec-1.png"),
                           "--generator", aspect_gen, "--to", str(d / "x.png"),
                           "--prompt", PROMPT]), 2)
        truthy("and nothing is placed", not (d / "x.png").exists())
        # One home inside another: the file is the deeper one's, and naming
        # that generator is not a contradiction.
        os.environ["CODEX_HOME"] = str(d)
        inner = recipe.home_of(aspect_gen)
        old_default = recipe.GENERATORS[aspect_gen]["home_default"]
        recipe.GENERATORS[aspect_gen]["home_default"] = str(d / "nested-home")
        try:
            got = recipe.generators_holding(d / "nested-home" / "a.jpg")
            check("the deepest home holding a file comes first",
                  got, [aspect_gen, recipe.DEFAULT_GENERATOR])
            made = d / "nested-home" / "brain" / "x" / "a.jpg"
            made.parent.mkdir(parents=True)
            made.write_bytes(jpeg_with(16, 16, []))
            check("--generator naming only the broader home's generator is refused",
                  recipe.main(["capture", "--from", str(made), "--generator",
                               recipe.DEFAULT_GENERATOR, "--to", str(d / "broad.jpg"),
                               "--prompt", PROMPT]), 2)
            check("--generator naming the deeper home's generator is accepted",
                  recipe.main(["capture", "--from", str(made), "--generator", aspect_gen,
                               "--to", str(d / "nested.jpg"), "--prompt", PROMPT]), 0)
            check("and without it the deeper home's generator is recorded",
                  recipe.main(["capture", "--from", str(made), "--to",
                               str(d / "nested2.jpg"), "--prompt", PROMPT]), 0)
            side = recipe.sidecar_of(d / "nested2.jpg").read_text(encoding="utf-8")
            truthy("its own invocation", recipe.GENERATORS[aspect_gen]["invoke"] in side)
        finally:
            recipe.GENERATORS[aspect_gen]["home_default"] = old_default
        check("home_of is restored", recipe.home_of(aspect_gen), inner)
    finally:
        if old is None:
            os.environ.pop("CODEX_HOME")
        else:
            os.environ["CODEX_HOME"] = old

    for flag in ("model", "engine", "excluded", "asked"):
        check(f"a blank --{flag} is refused before anything is placed",
              capture(d, f"blank-{flag}.png", **{flag: "  "}), 2)
        truthy(f"so a blank --{flag} leaves no asset behind",
               not (d / f"blank-{flag}.png").exists())
    for i, spec in enumerate(("", ":role")):
        check(f"--input {spec!r} names no path and is refused",
              capture(d, f"no-path-{i}.png", input=spec), 2)
        truthy(f"and --input {spec!r} places nothing", not (d / f"no-path-{i}.png").exists())

    (d / "src.png").write_bytes(png(64, 32))
    (d / "refs").mkdir()
    (d / "refs" / "shot 12:30.png").write_bytes(png(8, 8))
    (d / "ref.png").write_bytes(png(8, 8))
    here = os.getcwd()
    os.chdir(d)                                # --from as a relative path
    try:
        check("capture with an input whose name holds a colon",
              recipe.main(["capture", "--from", "src.png", "--to", str(d / "colon.png"),
                           "--prompt", PROMPT, "--generator", recipe.DEFAULT_GENERATOR,
                           "--input", "refs/shot 12:30.png:edit target",
                           "--input", "ref.png:mask: inpaint the sky"]), 0)
    finally:
        os.chdir(here)
    doc = yaml.safe_load(recipe.sidecar_of(d / "colon.png").read_text(encoding="utf-8"))
    check("the split is where the path that exists ends, on either side of a colon",
          doc["inputs"], [{"path": "refs/shot 12:30.png", "role": "edit target"},
                          {"path": "ref.png", "role": "mask: inpaint the sky"}])
    (d / "refs" / "shot 12").write_bytes(png(8, 8))      # now both splits name a file
    os.chdir(d)
    try:
        check("an input two splits could both name is refused, not guessed",
              recipe.main(["capture", "--from", "src.png", "--to", str(d / "ambig.png"),
                           "--prompt", PROMPT, "--generator", recipe.DEFAULT_GENERATOR,
                           "--input", "refs/shot 12:30.png:edit target"]), 2)
    finally:
        os.chdir(here)
    truthy("and nothing is placed", not (d / "ambig.png").exists())
    check("output.generated is absolute, so it names the file from anywhere",
          doc["output"]["generated"], str(d / "src.png"))
    check("and the recipe capture wrote passes check",
          recipe.check_one(d / "colon.png"), [])

    side = recipe.sidecar_of(d / "colon.png")
    good = side.read_text(encoding="utf-8")
    for value in (None, "", ["x"]):
        doc = yaml.safe_load(good)
        doc["size"]["asked"] = value
        side.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        truthy(f"size.asked {value!r} is reported",
               any("size.asked" in p for p in recipe.check_one(d / "colon.png")))
    doc = yaml.safe_load(good)
    del doc["size"]["asked"]
    side.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    truthy("a size with no asked half is reported",
           any("size.asked" in p for p in recipe.check_one(d / "colon.png")))
    side.write_text(good, encoding="utf-8")

    e = d / "odd"
    e.mkdir()
    (e / "a.png").write_bytes(png(8, 8))                 # no recipe: a problem
    (e / "c.png").write_bytes(png(8, 8))
    recipe.sidecar_of(e / "c.png").mkdir()               # a directory, not a recipe
    truthy("a sidecar that is a directory is a problem, not a traceback",
           recipe.check_one(e / "c.png"))
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        rc = recipe.main(["check", "--dir", str(e)])
    check("and check --dir still reaches every other image",
          (rc, said.getvalue().splitlines()[-1]), (1, "2 image(s), 2 problem(s)"))
    check("show says so too", recipe.main(["show", str(e / "c.png")]), 0)


def test_strip_round_five(tmp: Path) -> None:
    """A scan cut at a filled restart, and blocks that kept or dropped the
    wrong thing by marker or tag alone."""
    f = tmp / "fill.jpg"
    head = jpeg_with(16, 16, [])[:-len(b"ENTROPY\xff\xd9")]
    entropy = b"AB\xff\xff\xd0CD\xff\xff\xff\xd1EF\xff\xff\x00GH"
    f.write_bytes(head + entropy + b"\xff\xd9")
    out, dropped, _ = strip.strip(f, Opt())
    truthy("fill bytes before a restart do not end the scan", entropy in out)
    check("and nothing in it is reported as stray", dropped, [])
    f.write_bytes(head + b"AB\xff\x4a\x00\x03\x00CDEFG" + b"\xff\xd9")
    truthy("bytes a scan's walk could not place are refused, not dropped as stray",
           refuses(f, Opt(), "after a scan began"))

    jfif = b"JFIF\x00\x01\x02\x00\x00\x01\x00\x01\x00\x00"
    f.write_bytes(jpeg_with(16, 16, [(0xE0, jfif + b"PROMPTTEXT")]))
    out, dropped, _ = strip.strip(f, Opt())
    truthy("bytes after a JFIF header with no thumbnail are removed",
           b"PROMPTTEXT" not in out and jfif in out)
    truthy("and reported", any("after the JFIF header" in d for d in dropped))

    jumbf = b"JP\x00\x01\x00\x00\x00\x01" + struct.pack(">I", 16) + b"jumb" + b"c2pa-box"
    xt = b"JP\x00\x01\x00\x00\x00\x01" + struct.pack(">I", 16) + b"priv" + b"SECRET2"
    f.write_bytes(jpeg_with(16, 16, [(0xEB, b"XMP\x00SECRET"), (0xEB, xt), (0xEB, jumbf)]))
    out, dropped, _ = strip.strip(f, Opt())
    truthy("an APP11 that is not JUMBF is removed", b"SECRET" not in out)
    truthy("nor is a JPEG XT box that only opens like one", b"SECRET2" not in out)
    truthy("a JUMBF APP11 is a credential and stays", jumbf in out)
    out, _, _ = strip.strip(f, Opt(drop_credentials=True))
    truthy("unless credentials are dropped", jumbf not in out)

    f = tmp / "c2pa.webp"
    f.write_bytes(webp_with(16, 16, 0, [(b"VP8L", b"\x2f" + bytes(4)),
                                        (b"C2PA", b"manifest")]))
    out, dropped, _ = strip.strip(f, Opt())
    truthy("a WebP C2PA chunk is a credential and stays", b"C2PA" in webp_tags(out))
    check("and nothing is reported", dropped, [])
    out, dropped, _ = strip.strip(f, Opt(drop_credentials=True))
    truthy("--drop-credentials removes it", b"C2PA" not in webp_tags(out))

    lossless = b"VP8L" + struct.pack("<I", 5) + b"\x2f" + bytes(4) + b"\x00"
    short = (b"VP8X" + struct.pack("<I", 0) + lossless)
    raw = b"RIFF" + struct.pack("<I", 4 + len(short)) + b"WEBP" + short
    truthy("a VP8X declaring too little to hold a size is Unreadable",
           raises(lambda: imgfacts.probe_bytes(raw), imgfacts.Unreadable))
    f = tmp / "short-vp8x.webp"
    f.write_bytes(raw)
    check("and strip says so rather than reading the next chunk",
          strip.main([str(f)]), 1)


def test_strip_concurrent_change(tmp: Path) -> None:
    """--in-place writes back only over the bytes it stripped. Another process
    changing the file in between keeps its change: the run refuses instead of
    overwriting it with a stripped copy of the old content — on both the
    atomic path and the write-through path."""
    import os
    d = tmp / "race"
    d.mkdir()
    junk = raw_chunk(b"tEXt", b"k\x00v")
    for linked in (False, True):
        f = d / f"race-{linked}.png"
        f.write_bytes(png(16, 16, extra=junk))
        if linked:
            os.link(f, d / f"race-{linked}-other.png")    # the write-through path
        newer = png(32, 32)                               # what the other writer saves
        real = strip.strip

        def strip_then_someone_saves(path, opt):
            result = real(path, opt)
            path.write_bytes(newer)
            return result

        strip.strip = strip_then_someone_saves
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                code = strip.main([str(f), "--in-place"])
        finally:
            strip.strip = real
        path = "write-through" if linked else "atomic"
        check(f"{path}: a file changed after stripping is refused", code, 1)
        check(f"{path}: and the other writer's change is kept", f.read_bytes(), newer)
        truthy(f"{path}: and the refusal says why", "changed" in err.getvalue())


def test_engine_integrity(tmp: Path) -> None:
    """A verdict is the engine's answer, from an engine allowed to give one, in
    the shape that was asked for — and the exit code says what was found."""
    import os
    good = {"refuted": False, "reason": "r", "what_would_settle_it": "w"}
    noise = json.dumps({"type": "telemetry",
                        "structured_output": dict(good, refuted=True)})
    os.environ["FAKE_NOISE"] = noise
    try:
        with fake_engines(tmp, good):
            check("a log line after the answer does not replace it",
                  engine.run("claude", "p", refute.SCHEMA), good)
    finally:
        os.environ.pop("FAKE_NOISE")
    truthy("two unlabelled objects are ambiguous, not a choice",
           raises(lambda: engine._parse("x", '{"a": 1}\n{"a": 2}'), engine.EngineError))

    for running in ("Claude", "nonsense"):
        check(f"--running {running!r} is refused even with a checker named",
              exits(lambda: engine.main(["--running", running, "codex", "--prompt-file",
                                         "p", "--schema", "s"])), 2)

    with fake_engines(tmp, good):
        # agy takes the prompt as an argument, where a NUL cannot go; stdin can
        # carry one. A lone surrogate cannot be encoded on either route.
        truthy("a NUL in an argument-borne prompt is an EngineError, not a traceback",
               raises(lambda: engine.run("agy", "a\x00b", refute.SCHEMA), engine.EngineError))
        for name in ("agy", "claude"):
            truthy(f"{name}: an unencodable prompt is an EngineError, not a traceback",
                   raises(lambda: engine.run(name, "a\ud800b", refute.SCHEMA),
                          engine.EngineError))

    with fake_engines(tmp, dict(good, ok=True)):
        truthy("a key the schema closed is outside it",
               raises(lambda: engine.run("claude", "p", refute.SCHEMA), engine.EngineError))
    check("enum is enforced", bool(engine.conforms("maybe", {"enum": ["yes", "no"]})), True)
    check("const is enforced", bool(engine.conforms(2, {"const": 1})), True)
    check("items are enforced",
          bool(engine.conforms([1, "x"], {"type": "array", "items": {"type": "integer"}})), True)
    check("so are list-form positional items",
          bool(engine.conforms(["bad"], {"type": "array", "items": [{"type": "integer"}]})), True)
    check("and prefixItems",
          bool(engine.conforms(["bad"], {"type": "array", "prefixItems": [{"type": "integer"}]})),
          True)
    check("and additionalItems: false past them",
          bool(engine.conforms([1, 2], {"items": [{"type": "integer"}],
                                        "additionalItems": False})), True)
    check("a list that fits its positional items conforms",
          engine.conforms([1, "a"], {"prefixItems": [{"type": "integer"}],
                                     "items": {"type": "string"}}), [])
    check("NaN is not a number", bool(engine.conforms(float("nan"), {"type": "number"})), True)
    check("infinity is not a number", bool(engine.conforms(float("inf"), {"type": "number"})), True)
    check("true is not the enum member 1", bool(engine.conforms(True, {"enum": [1]})), True)
    check("false is not the const 0", bool(engine.conforms(False, {"const": 0})), True)
    check("nor inside an object", bool(engine.conforms({"x": True}, {"const": {"x": 1}})), True)
    check("nor inside an array", bool(engine.conforms([True], {"enum": [[1]]})), True)
    check("an equal nested value still conforms",
          engine.conforms({"x": [1, True]}, {"const": {"x": [1, True]}}), [])
    optional = {"type": "object", "properties": {"ok": {"type": "boolean"},
                                                 "note": {"type": "string"}},
                "required": ["ok"]}
    with fake_engines(tmp, {"ok": True, "note": "n"}) as log:
        engine.run("claude", "p", optional)
        told = json.loads(log.read_text().splitlines()[-1])["argv"]
        check("claude is told the closed schema its answer is checked against",
              json.loads(told[told.index("--json-schema") + 1]),
              engine.strict(optional))
    sfile = tmp / "list.json"
    sfile.write_text("[]", encoding="utf-8")
    (tmp / "p.txt").write_text("p", encoding="utf-8")
    check("a schema that is not an object exits 2",
          engine.main(["--running", "claude", "codex", "--prompt-file",
                       str(tmp / "p.txt"), "--schema", str(sfile)]), 2)

    pidfile = tmp / "grandchild.pid"
    os.environ["FAKE_SPAWN"] = str(pidfile)
    saved_timeout, engine.TIMEOUT = engine.TIMEOUT, 2
    try:
        with fake_engines(tmp, good):
            truthy("a timeout is an EngineError",
                   raises(lambda: engine.run("claude", "p", refute.SCHEMA), engine.EngineError))
    finally:
        engine.TIMEOUT = saved_timeout
        os.environ.pop("FAKE_SPAWN")
    if pidfile.exists():
        check("and the engine's whole process tree is gone, not just its parent",
              alive(int(pidfile.read_text())), False)

    # Ctrl-C reaches Python, not the engine's own session: the tree must still go.
    # agy, because its prompt is an argument: the fake reads no stdin first.
    pidfile.unlink(missing_ok=True)
    os.environ["FAKE_SPAWN"] = str(pidfile)
    real = subprocess.Popen.communicate

    def interrupted(self, *args, **kw):
        import time
        for _ in range(100):
            if pidfile.exists() and pidfile.read_text():
                break
            time.sleep(0.05)
        raise KeyboardInterrupt
    subprocess.Popen.communicate = interrupted
    try:
        with fake_engines(tmp, good):
            truthy("an interrupt is passed on",
                   raises(lambda: engine.run("agy", "p", refute.SCHEMA), KeyboardInterrupt))
    finally:
        subprocess.Popen.communicate = real
        os.environ.pop("FAKE_SPAWN")
    check("and the engine's tree does not outlive it", alive(int(pidfile.read_text())), False)

    claims = tmp / "verdict.json"
    claims.write_text(json.dumps([{"id": "c1", "claim": "the file is 1536x1024"}]))
    with fake_engines(tmp, dict(good, refuted=True)):
        check("a refuted claim exits 3, not 0",
              refute.main(["--running", "claude", str(claims)]), 3)
    os.environ["FAKE_ONLY"] = "codex"
    try:
        with fake_engines(tmp, good):
            check("a claim only some refuters read exits 1, not 0",
                  refute.main(["--running", "claude", str(claims)]), 1)
    finally:
        os.environ.pop("FAKE_ONLY")
    real_pool = refute.refuters
    refute.refuters = lambda running: []
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            check("no refuter at all leaves every claim unchecked, and exits 1",
                  refute.main(["--running", "claude", str(claims)]), 1)
    finally:
        refute.refuters = real_pool


def test_engine_failures(tmp: Path) -> None:
    """An engine that said it failed, or answered in bytes nobody can read, did
    not answer — and one engine failing that way leaves the others' verdicts."""
    import os
    good = {"refuted": False, "reason": "r", "what_would_settle_it": "w"}

    def answer_or_error(fn):
        try:
            return fn()
        except engine.EngineError as e:
            return f"EngineError: {e}"

    def under(flag: str, value: str, fn):
        os.environ[flag] = value
        try:
            return fn()
        finally:
            os.environ.pop(flag)

    for name in engine.ENGINES["runs_on"]:
        with fake_engines(tmp, good):
            truthy(f"{name}: a conforming answer from an engine that exited 1 is no answer",
                   under("FAKE_RC", "1", lambda: raises(
                       lambda: engine.run(name, "p", refute.SCHEMA), engine.EngineError)))
            truthy(f"{name}: an answer that is not UTF-8 is an EngineError, not a traceback",
                   under("FAKE_BYTES", "1", lambda: raises(
                       lambda: engine.run(name, "p", refute.SCHEMA), engine.EngineError)))
            check(f"{name}: a log on stderr that is not UTF-8 does not cost the answer",
                  under("FAKE_STDERR_BYTES", "1", lambda: answer_or_error(
                      lambda: engine.run(name, "p", refute.SCHEMA))), good)
        with fake_engines(tmp, dict(good, reason="a\ud800b")):
            truthy(f"{name}: an answer holding a lone surrogate is an EngineError",
                   raises(lambda: engine.run(name, "p", refute.SCHEMA), engine.EngineError))
    for name in ("claude", "agy"):
        with fake_engines(tmp, good):
            truthy(f"{name}: an envelope marked is_error is no answer",
                   under("FAKE_IS_ERROR", "1", lambda: raises(
                       lambda: engine.run(name, "p", refute.SCHEMA), engine.EngineError)))

    claims = tmp / "failures.json"
    claims.write_text(json.dumps([{"id": "c1", "claim": "the file is 1536x1024"}]))
    with fake_engines(tmp, good):
        check("refute: a run where every engine exited 1 is unchecked, not unrefuted",
              under("FAKE_RC", "1", lambda: refute.main(["--running", "codex", str(claims)])), 1)
    with fake_engines(tmp, dict(good, refuted=True, reason="a\ud800b")):
        for extra in ([], ["--json"]):
            check(f"refute {extra}: an unprintable reason does not crash the run",
                  refute.main(["--running", "codex", *extra, str(claims)]), 1)

    p = tmp / "p.txt"
    p.write_text("p", encoding="utf-8")
    sfile = tmp / "broken.json"
    for bad in ({"type": 5}, {"type": {"x": 1}}, {"type": "objekt"},
                {"type": "object", "properties": ["a"]},
                {"type": "object", "required": "a"},
                {"type": "object", "properties": {"rows": {"type": "array",
                                                           "items": {"type": 7}}}}):
        sfile.write_text(json.dumps(bad), encoding="utf-8")
        with fake_engines(tmp, {"a": 1}) as log:
            check(f"a malformed schema {bad!r} exits 2",
                  engine.main(["--running", "claude", "codex", "--prompt-file", str(p),
                               "--schema", str(sfile)]), 2)
            check("and no engine is paid to answer it", log.read_text(), "")

    # The locale is fixed when Python starts, so this one runs in a child under
    # the C locale, where text-mode pipes are ASCII.
    probe = ("import json, pathlib, sys; sys.path.insert(0, sys.argv[1]); "
             "import test_tools as t; "
             "good = dict(refuted=False, reason='\\u7406\\u7531', what_would_settle_it='w'); "
             "ctx = t.fake_engines(pathlib.Path(sys.argv[2]), good); ctx.__enter__(); "
             "print(json.dumps([t.engine.run(n, '\\u753b\\u50cf', t.refute.SCHEMA) == good "
             "for n in ('claude', 'codex')]))")
    child = subprocess.run([sys.executable, "-c", probe, str(Path(__file__).resolve().parent),
                            str(tmp)], capture_output=True, text=True, encoding="utf-8",
                           env=dict(os.environ, LC_ALL="C", LANG="C", PYTHONUTF8="0",
                                    PYTHONCOERCECLOCALE="0", PYTHONIOENCODING="utf-8"))
    check("under the C locale a non-ASCII prompt and answer still go through",
          child.stdout.strip() or child.stderr.strip()[-300:], "[true, true]")

    untyped = {"type": "object", "properties": {"rows": {"type": "array", "items": {
        "properties": {"v": {"type": "integer"}}}}}}
    truthy("an object schema without `type` is closed too",
           engine.conforms({"rows": [{"v": 1, "stowaway": "x"}]}, engine.strict(untyped)))


def alive(pid: int) -> bool:
    """Whether `pid` still runs — a zombie awaiting its reaper does not; one
    found running is killed so that a failed check leaves nothing behind."""
    import os
    import time
    time.sleep(0.2)
    try:
        state = Path(f"/proc/{pid}/stat").read_text().split(")")[-1].split()[0]
    except OSError:
        return False
    if state != "Z":
        os.kill(pid, 9)
    return state != "Z"


def test_recipe_integrity(tmp: Path) -> None:
    """A capture either places the image and its recipe together, under names it
    reserved, or places nothing — and check reads what a recipe says, not only
    whether its keys are there."""
    import os
    import threading
    d = tmp / "integ"
    d.mkdir()
    src = d / "src.png"
    src.write_bytes(png(64, 32))
    outside = d / "outside"
    outside.mkdir()

    def cap(dest, *extra):
        with contextlib.redirect_stderr(io.StringIO()):
            return recipe.main(["capture", "--from", str(src), "--generator", "codex",
                                "--to", str(dest), "--prompt", PROMPT, *extra])

    dangling = d / "dangling.png"
    dangling.symlink_to(outside / "victim.png")
    check("a dangling symlink as --to is refused", cap(dangling), 2)
    check("and nothing was written through it", (outside / "victim.png").exists(), False)
    keep = outside / "keep.png"
    keep.write_bytes(png(10, 10))
    linked = d / "linked.png"
    linked.symlink_to(keep)
    check("a symlink to another file is refused even with --replace",
          cap(linked, "--replace"), 2)
    check("and that file is untouched", imgfacts.probe(keep)["size"], "10x10")
    hard = d / "hard.png"
    os.link(src, hard)
    check("a hard link to the generated file is refused, not a traceback",
          cap(hard, "--replace"), 2)

    deep = d / "long"
    deep.mkdir()
    name = "x" * 248 + ".png"                # its sidecar name is too long
    check("a recipe that cannot be written fails the capture", cap(deep / name), 2)
    check("and leaves no image without its recipe", sorted(deep.iterdir()), [])

    # The recipe failing after the image is in place takes the image back out.
    roll = d / "roll"
    roll.mkdir()
    real_replace, calls = recipe.os.replace, []

    def second_fails(a_, b_):
        calls.append(b_)
        if len(calls) == 2:
            raise OSError(28, "No space left on device")
        return real_replace(a_, b_)

    recipe.os.replace = second_fails
    try:
        check("a recipe that fails after the image was placed fails the capture",
              cap(roll / "h.png"), 2)
    finally:
        recipe.os.replace = real_replace
    check("and the image placed before it is taken back out",
          sorted(x.name for x in roll.iterdir()), [])

    # With --replace the image placed first was over an old one: a failure
    # puts the old one back rather than leaving its recipe beside nothing.
    check("a capture to replace", cap(roll / "h.png"), 0)
    old = {x.name: x.read_bytes() for x in roll.iterdir()}
    src.write_bytes(png(48, 32))
    calls.clear()
    recipe.os.replace = second_fails
    try:
        check("a --replace whose recipe fails fails the capture",
              cap(roll / "h.png", "--replace"), 2)
    finally:
        recipe.os.replace = real_replace
        src.write_bytes(png(64, 32))
    check("and the old image and recipe are both still there, unchanged",
          {x.name: x.read_bytes() for x in roll.iterdir()}, old)

    # If putting the old image back fails too, its copy is the only one left:
    # it is kept and named, not cleaned up with the temporaries.
    def second_and_third_fail(a_, b_):           # the recipe's placement, then
        calls.append(b_)                          # putting the image back
        if len(calls) == 2 or (len(calls) > 2 and Path(b_).name == "h.png"):
            raise OSError(30, "Read-only file system")
        return real_replace(a_, b_)

    calls.clear()
    src.write_bytes(png(48, 32))
    recipe.os.replace = second_and_third_fail
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            code = recipe.main(["capture", "--from", str(src), "--generator", "codex",
                                "--to", str(roll / "h.png"), "--prompt", PROMPT,
                                "--replace"])
    finally:
        recipe.os.replace = real_replace
        src.write_bytes(png(64, 32))
    check("a rollback that fails too is a failure of its own", code, 1)
    saved = [x for x in roll.iterdir() if x.name.startswith(".capture.")]
    check("and the old image survives in the copy the message names",
          [(x.read_bytes(), str(x) in err.getvalue()) for x in saved],
          [(old["h.png"], True)])
    for x in saved:
        x.unlink()
    (roll / "h.png").write_bytes(old["h.png"])      # put back what the failure left

    # The same, on a directory where the temporaries cannot be removed either:
    # that cleanup failing must not replace the error naming the saved copy.
    real_unlink = Path.unlink

    def stuck(self, missing_ok=False):
        if self.name.startswith(".capture."):
            raise OSError(30, "Read-only file system")
        return real_unlink(self, missing_ok=missing_ok)

    calls.clear()
    src.write_bytes(png(48, 32))
    recipe.os.replace, Path.unlink = second_and_third_fail, stuck
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            code = recipe.main(["capture", "--from", str(src), "--generator", "codex",
                                "--to", str(roll / "h.png"), "--prompt", PROMPT,
                                "--replace"])
    finally:
        recipe.os.replace, Path.unlink = real_replace, real_unlink
        src.write_bytes(png(64, 32))
    check("a cleanup that fails too still reports where the old image is",
          (code, "Move it back by hand" in err.getvalue()), (1, True))
    for x in roll.iterdir():
        if x.name.startswith(".capture."):
            x.unlink()
    (roll / "h.png").write_bytes(old["h.png"])

    # Two captures into one directory place one after the other: one held
    # the lock, so the other waits rather than interleaving its renames.
    import fcntl
    roll_old = (roll / "h.png").read_bytes()
    held = os.open(roll, os.O_RDONLY)
    fcntl.flock(held, fcntl.LOCK_EX)
    codes = []
    t = threading.Thread(target=lambda: codes.append(cap(roll / "h.png", "--replace")))
    try:
        src.write_bytes(png(48, 32))
        t.start()
        t.join(0.5)
        check("a capture waits while another holds its directory",
              ((roll / "h.png").read_bytes() == roll_old, codes), (True, []))
    finally:
        fcntl.flock(held, fcntl.LOCK_UN)
        os.close(held)
        t.join(10)
        src.write_bytes(png(64, 32))
    check("and places once the other is done", codes, [0])

    # An interrupt landing right after a rename: the name it replaced is
    # still put back, because it was owned before the rename ran.
    (roll / "h.png").write_bytes(old["h.png"])
    def interrupted_after(a_, b_):
        real_replace(a_, b_)
        if Path(b_).name == "h.png":
            raise KeyboardInterrupt
    src.write_bytes(png(48, 32))
    recipe.os.replace = interrupted_after
    try:
        truthy("an interrupt after the image rename is passed on",
               raises(lambda: cap(roll / "h.png", "--replace"), KeyboardInterrupt))
    finally:
        recipe.os.replace = real_replace
        src.write_bytes(png(64, 32))
    check("and the image it replaced is back", (roll / "h.png").read_bytes(), old["h.png"])

    # A new capture whose undoing fails says what it left, not that nothing was.
    fresh = d / "fresh"
    fresh.mkdir()
    calls.clear()
    real_unlink = Path.unlink

    def stuck_new(self, missing_ok=False):
        if self.parent == fresh and not self.name.startswith(".capture."):
            raise OSError(30, "Read-only file system")
        return real_unlink(self, missing_ok=missing_ok)

    recipe.os.replace, Path.unlink = second_fails, stuck_new
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            code = recipe.main(["capture", "--from", str(src), "--generator", "codex",
                                "--to", str(fresh / "n.png"), "--prompt", PROMPT])
    finally:
        recipe.os.replace, Path.unlink = real_replace, real_unlink
    check("a new capture that cannot be undone reports what it left",
          (code, str(fresh / "n.png") in err.getvalue(),
           "nothing was written" in err.getvalue()), (1, True, False))

    cut = d / "cut.png"
    cut.write_bytes(png(64, 32)[:-12])        # no IEND: still being written
    with contextlib.redirect_stderr(io.StringIO()):
        code = recipe.main(["capture", "--from", str(cut), "--generator", "codex",
                            "--to", str(d / "cut-out.png"), "--prompt", PROMPT])
    check("a file that is not complete yet is not captured", code, 2)
    check("bytes appended after IEND do not hide it",
          imgfacts.complete(png(64, 32) + b"\x00" * 100), True)
    data = b"\x05\x3b\x3b\x01\x02\x3b"                   # 0x3B inside image data
    whole = (gif(2, 2) + b"\x2c" + struct.pack("<HHHH", 0, 0, 2, 2) + b"\x00"
             + b"\x02" + bytes([len(data)]) + data + b"\x00" + b"\x3b")
    check("a GIF read block by block reaches its trailer", imgfacts.complete(whole), True)
    check("a GIF cut where its image data holds a 0x3B is not complete",
          [n for n in range(len(whole)) if imgfacts.complete(whole[:n])], [])

    # Two captures racing to one name: one wins, the other is refused, and
    # the image and recipe that land are from the same run.
    real_probe, codes = imgfacts.probe_bytes, []

    def slow(*args):
        import time
        time.sleep(0.3)
        return real_probe(*args)

    imgfacts.probe_bytes = slow
    try:
        racers = [threading.Thread(target=lambda: codes.append(cap(d / "race.png")))
                  for _ in range(2)]
        for r in racers:
            r.start()
        for r in racers:
            r.join()
    finally:
        imgfacts.probe_bytes = real_probe
    check("of two captures to one name, exactly one succeeds", sorted(codes), [0, 2])

    # The source rewritten after its check: what lands is what was checked.
    real_complete = imgfacts.complete
    checked = src.read_bytes()

    def then_rewritten(raw):
        src.write_bytes(checked[:-12])       # cut short, as a writer mid-save
        return real_complete(raw)

    imgfacts.complete = then_rewritten
    try:
        check("a capture whose source changes after the check still succeeds",
              cap(d / "snap.png"), 0)
    finally:
        imgfacts.complete = real_complete
        src.write_bytes(checked)
    check("and places the bytes it checked, not the ones written since",
          (d / "snap.png").read_bytes(), checked)

    good = d / "good.png"
    check("a capture still works", cap(good), 0)
    side = recipe.sidecar_of(good)
    original = side.read_text(encoding="utf-8")
    for change, says in (
            ({"output": {"note": "x"}}, "output.placed"),
            ({"output": {"placed": None, "generated": "g"}}, "output.placed"),
            ({"inputs": 5}, "inputs"),
            ({"inputs": [{"path": "brand/mark.png"}]}, "inputs"),
            ({"inputs": [{"path": "brand/mark.png", "role": " "}]}, "inputs"),
            ({"engine": 0}, "engine"),
            ({"model": False}, "model"),
            ({"excluded": []}, "excluded")):
        doc = yaml.safe_load(original)
        doc.update(change)
        side.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        truthy(f"check reports a malformed {says}",
               any(says in p for p in recipe.check_one(good)))
    side.write_bytes(original.encode("utf-8") + b"\xff\xfe")
    truthy("a sidecar that is not UTF-8 is a problem, not a traceback",
           any("UTF-8" in p for p in recipe.check_one(good)))
    side.write_text(original, encoding="utf-8")
    (d / "folder.png").mkdir()
    with contextlib.redirect_stdout(io.StringIO()):
        recipe.main(["check", "--dir", str(d)])          # must not treat it as an image
    check("a directory named like an image is not checked as one",
          any("folder.png" in p for p in recipe.check_one(d / "good.png")), False)


def test_cli_bounds_and_render_sections(tmp: Path) -> None:
    """Numbers past any canvas, the wrong lever, and sections found by text
    that only looked like their heading."""
    huge = "1" + "0" * 400
    for args in ([f"--check-size={huge}x16"], [f"--check-aspect=1:{huge}"],
                 [f"--check-aspect={huge}:1"]):
        with contextlib.redirect_stderr(io.StringIO()):
            check(f"{args[0][:24]}… is refused as input, not a traceback",
                  exits(lambda: imgfacts.main(args)), 2)
    aspect_gen = sorted(imgfacts.ASPECT_GENERATORS)[0]
    with contextlib.redirect_stderr(io.StringIO()):
        check("--check-size asked of a generator that takes no pixel size is refused",
              imgfacts.main(["--check-size", "1024x1024", "--generator", aspect_gen]), 2)

    key, spec = next(iter(render.H["delivered"].items()))
    section = spec["section"]
    block = f"<!-- deliver:{key} -->"
    cases = {
        "an H3 with the same words is not the section":
            f"# T\n\n### {section}\n\nsub\n\n## {section}\n\nreal\n\n## Next\n",
        "a heading inside a fence is not the section":
            f"# T\n\n```\n## {section}\n```\n\n## {section}\n\nreal\n\n## Next\n",
        "an H1 ends the section":
            f"# T\n\n## {section}\n\nreal\n\n# Appendix\n\nlater\n",
        "hashes with no space before them are text, not a closing sequence":
            f"# T\n\n## {section}###\n\nwrong\n\n## {section}\n\nreal\n\n## Next\n",
        "a backtick run whose info string holds a backtick opens no fence":
            f"# T\n\n```bad`info\n\n## {section}\n\nreal\n\n## Next\n",
    }
    for name, text in cases.items():
        f = tmp / "render-case.md"
        f.write_text(text, encoding="utf-8")
        render.render(f)
        out = f.read_text(encoding="utf-8")
        at = out.find(block)
        real = out.find("real")
        after = min(i for i in (out.find("## Next"), out.find("# Appendix"), len(out))
                    if i != -1)
        truthy(name, at > real and at < after)


def exits(fn) -> int:
    try:
        return fn()
    except SystemExit as e:                    # argparse .error()
        return e.code


def test_cli_surfaces(tmp: Path) -> None:
    """The entry points a person actually types."""
    check("imgfacts --json over several files",
          imgfacts.main([str(tmp / "hero.png"), "--json"]), 0)
    check("imgfacts --check-size --json", imgfacts.main(
        ["--check-size", "1000x1000", "--json"]), 1)
    check("imgfacts with no arguments explains itself", imgfacts.main([]), 2)
    check("recipe show prints a recipe",
          recipe.main(["show", str(tmp / "hero.png")]), 0)
    check("recipe show on an image with none",
          recipe.main(["show", str(tmp / "orphan.png")]), 0)
    check("recipe check with nothing to check",
          recipe.main(["check"]), 2)


def main() -> int:
    # The tools talk to a person; here only the results should. Their own output
    # is exercised (every path below runs it) and then thrown away.
    noise = io.StringIO()
    with tempfile.TemporaryDirectory() as d, \
            contextlib.redirect_stdout(noise), contextlib.redirect_stderr(noise):
        tmp = Path(d)
        test_imgfacts(tmp)
        test_legality()
        test_nearest_legal_at_the_edge()
        test_aspect_legality()
        test_recipe(tmp)
        test_recipe_verbatim(tmp)
        test_recipe_generators(tmp)
        test_recipe_hardening(tmp)
        test_recipe_integrity(tmp)
        test_strip(tmp)
        test_no_writes_while_reporting(tmp)
        test_malformed_input(tmp)
        test_strip_leaks(tmp)
        test_strip_writes(tmp)
        test_strip_concurrent_change(tmp)
        test_strip_round_five(tmp)
        test_recipe_round_five(tmp)
        test_strip_accounts_for_every_byte(tmp)
        test_cli_surfaces(tmp)
        test_cli_bounds_and_render_sections(tmp)
        test_engine(tmp)
        test_engine_integrity(tmp)
        test_engine_failures(tmp)
        test_precommit_hook(tmp)
        test_edges_round_four(tmp)
    if failures:
        print(f"{len(failures)} failure(s):")
        print("\n".join(failures))
        return 1
    print(f"tools green - imgfacts read PNG, JPEG, WebP and GIF headers; "
          f"canvas legality checked both ways and the aspect list both ways; "
          f"each of {len(recipe.GENERATORS)} generators captured under its own "
          f"invocation; recipe round-tripped and caught "
          f"each of {len(recipe.FIELDS)} fields missing; short/Unicode/CRLF prompts preserved verbatim; strip kept and removed "
          f"the right blocks in 3 formats and refused 3 ways; "
          f"every CLI entry point exercised")
    return 0


if __name__ == "__main__":
    sys.exit(main())
