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
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True
import imgfacts                                            # noqa: E402
import recipe                                              # noqa: E402
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
    chunk = b"VP8L" + struct.pack("<I", len(body)) + body
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
            "--prompt", kw.pop("prompt", PROMPT)]
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

    # a prompt shortened to a summary is not a prompt
    side.write_text(good.replace(
        "prompt: |\n  Use case: stylized-concept\n  Primary request: a red circle",
        "prompt: a red circle"))
    truthy("a stub prompt is reported",
           any("verbatim" in p for p in recipe.check_one(tmp / "hero.png")))
    side.write_text(good)

    # an image with no recipe is not silently fine
    (tmp / "orphan.png").write_bytes(png(16, 16))
    truthy("an image with no recipe is reported",
           any("no recipe" in p for p in recipe.check_one(tmp / "orphan.png")))
    check("check --dir exits non-zero when something is missing",
          recipe.main(["check", "--dir", str(tmp)]), 1)
    check("capture without a prompt is refused", capture_no_prompt(tmp), 2)


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
        (0xEB, b"JP\x00\x00" + b"c2pa" + b"\x00" * 8),
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
    real = Path.write_bytes

    def spy(self, data):
        seen.append(str(self))
        return real(self, data)

    Path.write_bytes = spy
    try:
        check("reporting exits 0", strip.main([str(f)]), 0)
        check("reporting writes nothing", seen, [])
        check("--out writes exactly one file",
              strip.main([str(f), "--out", str(tmp / "sub" / "o.png")]), 0)
        check("and that file is the destination", seen, [str(tmp / "sub" / "o.png")])
    finally:
        Path.write_bytes = real
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
        test_aspect_legality()
        test_recipe(tmp)
        test_recipe_generators(tmp)
        test_strip(tmp)
        test_no_writes_while_reporting(tmp)
        test_cli_surfaces(tmp)
    if failures:
        print(f"{len(failures)} failure(s):")
        print("\n".join(failures))
        return 1
    print(f"tools green - imgfacts read PNG, JPEG, WebP and GIF headers; "
          f"canvas legality checked both ways and the aspect list both ways; "
          f"each of {len(recipe.GENERATORS)} generators captured under its own "
          f"invocation; recipe round-tripped and caught "
          f"each of {len(recipe.FIELDS)} fields missing; strip kept and removed "
          f"the right blocks in 3 formats and refused 3 ways; "
          f"every CLI entry point exercised")
    return 0


if __name__ == "__main__":
    sys.exit(main())
