#!/usr/bin/env python3
"""Read what is actually in an image file.

`_image/CONTRACT.md` grades a claim `measured` only when a property was read off
the file. This is the tool that makes that cheap, so that "1536x1024" in a report
is a fact rather than a repetition of what the prompt asked for.

    python3 image-tools/imgfacts.py hero.png
    python3 image-tools/imgfacts.py --json assets/*.png
    python3 image-tools/imgfacts.py --check-size 1536x1024

No image library, deliberately: this runs inside a skill on whatever machine the
skill is on. It parses headers rather than decoding pixels, so it is fast, it
never re-encodes anything, and the only import beyond the standard library is
the PyYAML the rest of the harness already needs — for the canvas constraints,
which live in the registry so that this and the reference page cannot disagree.

What it cannot do is judge the picture. Dimensions, format, bytes, whether there
is an alpha channel and whether a colour profile is declared are all it knows.
Six fingers is still a job for somebody who opened the image and looked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CANVAS = yaml.safe_load(
    (ROOT / "image-registry" / "harness.yaml").read_text(encoding="utf-8")
)["generator"]["canvas"]


class Unreadable(Exception):
    """The bytes are not an image this tool knows how to read."""


# --- PNG ---------------------------------------------------------------------

PNG_SIG = b"\x89PNG\r\n\x1a\n"
# colour type -> (name, has alpha channel)
PNG_COLOUR = {0: ("greyscale", False), 2: ("truecolour", False),
              3: ("indexed", False), 4: ("greyscale", True),
              6: ("truecolour", True)}


def _png(b: bytes) -> dict:
    if len(b) < 33 or b[12:16] != b"IHDR":
        raise Unreadable("PNG signature with no IHDR")
    w, h, depth, colour = struct.unpack(">IIBB", b[16:26])
    if colour not in PNG_COLOUR:
        raise Unreadable(f"PNG colour type {colour}")
    kind, alpha = PNG_COLOUR[colour]
    chunks = set()
    i = 8
    while i + 8 <= len(b):
        size, tag = struct.unpack(">I4s", b[i:i + 8])
        chunks.add(tag.decode("latin-1"))
        if tag == b"IDAT":                       # metadata all precedes the data
            break
        i += 12 + size
        if size > len(b):                        # truncated or lying length
            break
    if "tRNS" in chunks:
        alpha = True                             # indexed or keyed transparency
    return {"format": "PNG", "width": w, "height": h, "alpha": alpha,
            "colour": _profile(chunks & {"iCCP", "sRGB", "cHRM", "gAMA"}),
            "notes": [f"{kind}, {depth}-bit"]}


def _profile(tags: set[str]) -> str:
    if "iCCP" in tags:
        return "ICC embedded"
    if "sRGB" in tags:
        return "sRGB tagged"
    if tags:
        return "gamma/chromaticity only"
    return "none declared"


# --- JPEG --------------------------------------------------------------------

SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
       0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
# Markers that carry no length field. Reading two bytes of "length" from one of
# these walks the parser off into the middle of a segment.
JPEG_STANDALONE = {0x01, 0xD8, 0xD9} | set(range(0xD0, 0xD8))


def jpeg_segments(raw: bytes):
    """Walk a JPEG's markers, and stop where the entropy-coded data starts.

    Yields `(marker, start, end, body)` per segment, with `body` None for a
    standalone marker. `start` includes any `0xFF` fill bytes that preceded the
    marker — the standard allows them, and a copier that emits `raw[start:end]`
    keeps the file byte-identical where it keeps a segment at all.

    Shared by the reader and the stripper on purpose: two parsers of one format
    is two chances to disagree about it, and they did.
    """
    i = 2 if raw.startswith(b"\xff\xd8") else 0
    while i + 1 < len(raw):
        if raw[i] != 0xFF:
            i += 1
            continue
        j = i
        while j + 1 < len(raw) and raw[j + 1] == 0xFF:
            j += 1                              # fill bytes before the marker
        marker = raw[j + 1]
        if marker == 0x00:                      # a stuffed byte, not a marker
            i = j + 2
            continue
        if marker in JPEG_STANDALONE:
            yield marker, i, j + 2, None
            i = j + 2
            continue
        if j + 4 > len(raw):
            return
        seg = struct.unpack(">H", raw[j + 2:j + 4])[0]
        end = j + 2 + seg
        yield marker, i, end, raw[j + 4:end]
        if marker == 0xDA:                      # the rest is entropy data
            return
        i = end


def _jpeg(b: bytes) -> dict:
    size, colour, notes = None, "none declared", []
    for marker, _, _, body in jpeg_segments(b):
        if body is None or marker == 0xDA:
            continue
        if marker in SOF and size is None:
            h, w = struct.unpack(">HH", body[1:5])
            size = (w, h)
            notes.append("progressive" if marker in (0xC2, 0xC6, 0xCA) else "baseline")
        elif marker == 0xE2 and body.startswith(b"ICC_PROFILE\x00"):
            colour = "ICC embedded"
        elif marker == 0xE1 and body.startswith(b"Exif\x00\x00"):
            notes.append("Exif present")
    if size is None:
        raise Unreadable("JPEG with no frame header")
    return {"format": "JPEG", "width": size[0], "height": size[1], "alpha": False,
            "colour": colour, "notes": notes}


# --- WebP --------------------------------------------------------------------

def _webp(b: bytes) -> dict:
    tag = b[12:16]
    if tag == b"VP8X":
        flags = b[20]
        w = int.from_bytes(b[24:27], "little") + 1
        h = int.from_bytes(b[27:30], "little") + 1
        return {"format": "WebP", "width": w, "height": h,
                "alpha": bool(flags & 0x10),
                "colour": "ICC embedded" if flags & 0x20 else "none declared",
                "notes": ["extended"] + (["animated"] if flags & 0x02 else [])}
    if tag == b"VP8L":
        bits = int.from_bytes(b[21:25], "little")
        return {"format": "WebP", "width": (bits & 0x3FFF) + 1,
                "height": ((bits >> 14) & 0x3FFF) + 1,
                "alpha": bool((bits >> 28) & 1),
                "colour": "none declared", "notes": ["lossless"]}
    if tag == b"VP8 ":
        if b[23:26] != b"\x9d\x01\x2a":
            raise Unreadable("WebP lossy frame with no start code")
        w, h = struct.unpack("<HH", b[26:30])
        return {"format": "WebP", "width": w & 0x3FFF, "height": h & 0x3FFF,
                "alpha": False, "colour": "none declared", "notes": ["lossy"]}
    raise Unreadable(f"WebP chunk {tag!r}")


# --- GIF ---------------------------------------------------------------------

def _gif(b: bytes) -> dict:
    w, h = struct.unpack("<HH", b[6:10])
    return {"format": "GIF", "width": w, "height": h,
            "alpha": b"\x21\xf9" in b[:4096],    # a graphic control extension
            "colour": "none declared", "notes": [b[:6].decode("latin-1")]}


READERS = [(PNG_SIG, _png), (b"\xff\xd8\xff", _jpeg), (b"GIF8", _gif)]


def probe(path: Path) -> dict:
    return probe_bytes(path.read_bytes(), str(path))


def probe_bytes(raw: bytes, name: str = "<bytes>") -> dict:
    """The same reading, from memory.

    A caller checking a candidate it has not written yet — `strip.py` verifying
    its own output before it touches the disk — must not have to create a file
    to find out what is in it. Writing beside the input made a report-only run
    fail on a read-only directory.
    """
    path = Path(name)
    out = None
    for sig, fn in READERS:
        if raw.startswith(sig):
            out = fn(raw)
            break
    if out is None and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        out = _webp(raw)
    if out is None:
        raise Unreadable(f"{path.name}: not a PNG, JPEG, WebP or GIF")
    w, h = out["width"], out["height"]
    if w <= 0 or h <= 0:
        raise Unreadable(f"{path.name}: header states {w}x{h}")
    g = math.gcd(w, h)
    out.update(path=str(path), bytes=len(raw),
               sha256=hashlib.sha256(raw).hexdigest()[:16],
               size=f"{w}x{h}", ratio=f"{w // g}:{h // g}",
               megapixels=round(w * h / 1_000_000, 2),
               breaks=sorted(illegal(w, h)))
    return out


# --- canvas legality ---------------------------------------------------------

def illegal(w: int, h: int) -> set[str]:
    """Which of the generator's four canvas constraints this size breaks.

    The numbers come from image-registry/harness.yaml and nowhere else, so this
    and the reference page cannot disagree about them.
    """
    broken = set()
    if max(w, h) > CANVAS["max_edge"]:
        broken.add("max edge")
    if w % CANVAS["edge_multiple"] or h % CANVAS["edge_multiple"]:
        broken.add("multiple of 16")
    if max(w, h) / min(w, h) > CANVAS["max_ratio"]:
        broken.add("ratio")
    if not CANVAS["min_pixels"] <= w * h <= CANVAS["max_pixels"]:
        broken.add("total pixels")
    return broken


# How far a candidate's aspect may drift before it stops being the same shape.
# Relative, so it means the same thing at any ratio. Inside it, the answer is
# whichever legal canvas is nearest in area — because a function called
# `nearest_legal` that returns four times the pixels for a fourth decimal place
# of aspect is not answering the question that was asked.
ASPECT_TOLERANCE = 0.005


def nearest_legal(w: int, h: int) -> tuple[int, int] | None:
    """The legal canvas nearest in area whose aspect is still this shape.

    Aspect is the constraint and area is the objective: a picture is composed
    for a shape, and the pixel count was a request the generator was free to
    ignore anyway. Candidates within `ASPECT_TOLERANCE` of the requested aspect
    compete on area alone; if the multiple-of-16 grid puts nothing inside that
    band, the least-drifting candidate wins instead, and it is still legal.

    `None` when no scaling of this aspect is legal, which is what a ratio past
    the limit means.
    """
    m = CANVAS["edge_multiple"]
    if max(w, h) / min(w, h) > CANVAS["max_ratio"]:
        return None
    aspect, want = w / h, w * h
    inside, outside = [], []
    for scale in (s / 100 for s in range(10, 1001)):
        cw = max(m, round(w * scale / m) * m)
        ch = max(m, round(h * scale / m) * m)
        if illegal(cw, ch):
            continue
        drift = abs(cw / ch - aspect) / aspect
        (inside if drift <= ASPECT_TOLERANCE else outside).append(
            ((abs(cw * ch - want), drift) if drift <= ASPECT_TOLERANCE
             else (drift, abs(cw * ch - want)), (cw, ch)))
    pool = inside or outside
    return min(pool)[1] if pool else None


# --- output ------------------------------------------------------------------

def render(f: dict) -> str:
    head = (f"{f['path']}\n"
            f"  {f['size']}  {f['ratio']}  {f['megapixels']} MP  "
            f"{f['format']}  {f['bytes']:,} bytes  sha256:{f['sha256']}")
    tail = (f"\n  alpha: {'yes' if f['alpha'] else 'no'}   "
            f"colour: {f['colour']}")
    if f["notes"]:
        tail += f"   {', '.join(f['notes'])}"
    if f["breaks"]:
        tail += ("\n  not a legal generator canvas: breaks "
                 + ", ".join(f["breaks"]))
    return head + tail


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("files", nargs="*", type=Path)
    p.add_argument("--json", action="store_true", help="one object per file")
    p.add_argument("--check-size", metavar="WxH",
                   help="ask whether a canvas is legal, without a file")
    a = p.parse_args(argv)

    if a.check_size:
        try:
            w, h = (int(x) for x in a.check_size.lower().split("x"))
        except ValueError:
            print(f"not a size: {a.check_size!r} (want WxH)", file=sys.stderr)
            return 2
        broken = sorted(illegal(w, h))
        near = None if not broken else nearest_legal(w, h)
        if a.json:
            print(json.dumps({"size": f"{w}x{h}", "legal": not broken,
                              "breaks": broken,
                              "nearest_legal": f"{near[0]}x{near[1]}" if near else None}))
        elif not broken:
            print(f"{w}x{h} is legal")
        else:
            print(f"{w}x{h} breaks {', '.join(broken)}"
                  + (f"; nearest legal is {near[0]}x{near[1]}" if near
                     else "; no size at this aspect is legal"))
        return 0 if not broken else 1

    if not a.files:
        p.print_usage(sys.stderr)
        return 2

    facts, bad = [], False
    for f in a.files:
        try:
            facts.append(probe(f))
        except (Unreadable, OSError, struct.error) as e:
            bad = True
            print(f"{f}: {e}", file=sys.stderr)
    if a.json:
        print(json.dumps(facts, indent=2))
    else:
        print("\n".join(render(f) for f in facts))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
