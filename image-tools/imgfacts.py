#!/usr/bin/env python3
"""Read what is actually in an image file.

`_image/CONTRACT.md` grades a claim `measured` only when a property was read off
the file. This is the tool that makes that cheap, so that "1536x1024" in a report
is a fact rather than a repetition of what the prompt asked for.

    python3 image-tools/imgfacts.py hero.png
    python3 image-tools/imgfacts.py --json assets/*.png
    python3 image-tools/imgfacts.py --check-size 1536x1024
    python3 image-tools/imgfacts.py --check-aspect 4:5

No image library, deliberately: this runs inside a skill on whatever machine the
skill is on. It parses headers rather than decoding pixels, so it is fast, it
never re-encodes anything, and the only import beyond the standard library is
the PyYAML the rest of the harness already needs — for the generators' size
constraints, which live in the registry so that this and the reference pages
cannot disagree.

The two generators constrain size differently and the answer is not the same
question: one takes pixel dimensions and rejects an illegal canvas, the other
takes an aspect ratio off a fixed list and takes no pixel count at all. Asking
`--check-size` about the second would answer about a lever it does not have,
so the aspect list gets its own check rather than being folded into the canvas one.

What it cannot do is judge the picture. Dimensions, format, bytes, whether there
is an alpha channel, whether a colour profile is declared, and an Exif
orientation that turns how the picture is shown are all it knows.
Six fingers is still a job for somebody who opened the image and looked.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GENERATORS = yaml.safe_load(
    (ROOT / "image-registry" / "harness.yaml").read_text(encoding="utf-8")
)["generators"]


def _by_control(kind: str) -> dict:
    """The generators the registry says control size this way, by name."""
    return {n: g for n, g in GENERATORS.items()
            if isinstance(g, dict) and g.get("control") == kind}


# One generator declares a canvas today. Resolving it by `control:` rather than
# by name means adding a second one is a registry edit, and the assert is what
# stops that edit from silently picking whichever came first in the file.
_canvas = _by_control("canvas")
assert len(_canvas) == 1, f"expected exactly one canvas generator, found {sorted(_canvas)}"
CANVAS_GENERATOR = next(iter(_canvas))
CANVAS = _canvas[CANVAS_GENERATOR]["canvas"]
ASPECT_GENERATORS = _by_control("aspect")

# Past any canvas or screen by orders of magnitude, and still small enough that
# the ratio and log arithmetic below stays inside a float. A larger number is
# a typo, and answering it would mean a traceback rather than an input error.
MAX_EDGE = 10**6


class Unreadable(Exception):
    """The bytes are not an image this tool knows how to read."""


# --- Exif orientation ----------------------------------------------------------

EXIF_SIG = b"Exif\x00\x00"


def exif_orientation(block: bytes) -> int | None:
    """The Exif orientation tag, or None when the block does not state one.

    The `Exif\x00\x00` prefix is optional here on purpose. A JPEG APP1 always
    carries it, a PNG `eXIf` chunk holds bare TIFF, and WebP encoders differ —
    so the caller hands over whatever the container held and this decides. An
    earlier version had each caller prepend the prefix, which for the WebP
    encoders that already write one produced `ExifExif\x00\x00...`, no
    recognisable TIFF header, no orientation found, and a sideways picture
    stripped without a word. Shared with `strip.py`, which refuses what this
    reports: two readers of one tag is two chances to disagree about it.
    """
    b = block[len(EXIF_SIG):] if block.startswith(EXIF_SIG) else block
    if len(b) < 8 or b[:2] not in (b"II", b"MM"):
        return None
    end = "<" if b[:2] == b"II" else ">"
    try:
        off = struct.unpack(end + "I", b[4:8])[0]
        count = struct.unpack(end + "H", b[off:off + 2])[0]
        for i in range(count):
            e = off + 2 + i * 12
            tag, typ, n = struct.unpack(end + "HHI", b[e:e + 8])
            # SHORT is what the standard says; LONG is what some writers use
            # and what common readers still honour, so it is read too.
            if tag == 0x0112 and typ == 3 and n == 1:
                return struct.unpack(end + "H", b[e + 8:e + 10])[0]
            if tag == 0x0112 and typ == 4 and n == 1:
                return struct.unpack(end + "I", b[e + 8:e + 12])[0]
    except (struct.error, IndexError):
        return None
    return None


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
    chunks, exif = set(), None
    i, data = 8, False
    while i + 8 <= len(b):
        size, tag = struct.unpack(">I4s", b[i:i + 8])
        data = data or tag == b"IDAT"
        if not data:                             # colour and alpha precede the data
            chunks.add(tag.decode("latin-1"))
        if tag == b"eXIf" and exif is None:      # which some writers put after it
            exif = b[i + 8:i + 8 + size]
        i += 12 + size
        if size > len(b):                        # truncated or lying length
            break
    if "tRNS" in chunks:
        alpha = True                             # indexed or keyed transparency
    return {"format": "PNG", "width": w, "height": h, "alpha": alpha,
            "colour": _profile(chunks & {"cICP", "iCCP", "sRGB", "cHRM", "gAMA"}),
            "notes": [f"{kind}, {depth}-bit"],
            "orientation": exif_orientation(exif) if exif else None}


def _profile(tags: set[str]) -> str:
    # cICP outranks every other colour chunk when a decoder honours it, and it
    # is what an HDR (PQ/HLG) file states its colour space in.
    if "cICP" in tags:
        return "cICP declared"
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
SOF_PROGRESSIVE = {0xC2, 0xC6, 0xCA, 0xCE}
SOF_LOSSLESS = {0xC3, 0xC7, 0xCB, 0xCF}
# Markers that carry no length field. Reading two bytes of "length" from one of
# these walks the parser off into the middle of a segment.
JPEG_STANDALONE = {0x01, 0xD8, 0xD9} | set(range(0xD0, 0xD8))


def jpeg_segments(raw: bytes, through_scans: bool = False):
    """Walk a JPEG's markers, and stop where the entropy-coded data starts.

    Yields `(marker, start, end, body)` per segment, with `body` None for a
    standalone marker. `start` includes any `0xFF` fill bytes that preceded the
    marker — the standard allows them, and a copier that emits `raw[start:end]`
    keeps the file byte-identical where it keeps a segment at all.

    With `through_scans`, the walk continues past each scan: the entropy-coded
    data is yielded as `(None, start, end, None)`, the segments a progressive
    file puts between scans follow as usual, and the walk ends at EOI. Whatever
    lies after EOI — an appended second JPEG with its own Exif, say — is not
    part of this image, and a caller can see where it starts from EOI's `end`.
    A reader needs none of that; a stripper that copied everything after the
    first scan verbatim shipped all of it.

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
        if j + 1 >= len(raw):                   # fill bytes and then the end
            return
        marker = raw[j + 1]
        if marker == 0x00:                      # a stuffed byte, not a marker
            i = j + 2
            continue
        if marker in JPEG_STANDALONE:
            yield marker, i, j + 2, None
            i = j + 2
            if marker == 0xD9 and through_scans:
                return
            continue
        if j + 4 > len(raw):
            return
        seg = struct.unpack(">H", raw[j + 2:j + 4])[0]
        end = j + 2 + seg
        yield marker, i, end, raw[j + 4:end]
        if marker == 0xDA:                      # the rest is entropy data
            if not through_scans:
                return
            k = _entropy_end(raw, end)
            yield None, end, k, None
            end = k
        i = end


def _entropy_end(raw: bytes, i: int) -> int:
    """Where a scan's entropy-coded data stops: the first `0xFF` that is not a
    stuffed zero or a restart marker. The end of the file if nothing is.

    Fill bytes may precede any marker, a restart included, so a run of `0xFF`
    is looked through before deciding. Stopping at `FF FF D0` cut the scan at
    its first restart, and the stripper dropped the rest as stray bytes."""
    while True:
        k = raw.find(b"\xff", i)
        if k < 0:
            return len(raw)
        m = k + 1
        while m < len(raw) and raw[m] == 0xFF:
            m += 1                              # fill bytes before the marker
        if m >= len(raw):
            return len(raw)
        nxt = raw[m]
        if nxt == 0x00 or 0xD0 <= nxt <= 0xD7:
            i = m + 1
            continue
        return k


def _jpeg(b: bytes) -> dict:
    size, colour, notes, turn = None, "none declared", [], None
    for marker, _, _, body in jpeg_segments(b):
        if body is None or marker == 0xDA:
            continue
        if marker in SOF and size is None:
            if len(body) < 5:
                raise Unreadable("JPEG frame header too short to state a size")
            h, w = struct.unpack(">HH", body[1:5])
            size = (w, h)
            notes.append("progressive" if marker in SOF_PROGRESSIVE
                         else "lossless" if marker in SOF_LOSSLESS
                         else "baseline" if marker == 0xC0 else "sequential")
        elif marker == 0xE2 and body.startswith(b"ICC_PROFILE\x00"):
            colour = "ICC embedded"
        elif marker == 0xE1 and body.startswith(EXIF_SIG):
            notes.append("Exif present")
            if turn is None:                     # the first Exif is the one read
                turn = exif_orientation(body)
    if size is None:
        raise Unreadable("JPEG with no frame header")
    return {"format": "JPEG", "width": size[0], "height": size[1], "alpha": False,
            "colour": colour, "notes": notes, "orientation": turn}


# --- WebP --------------------------------------------------------------------

def _webp(b: bytes) -> dict:
    tag = b[12:16]
    # A header cut short reads as zeros, and zero plus one is a confident 1x1.
    need = {b"VP8X": 30, b"VP8L": 25, b"VP8 ": 30}.get(tag)
    if need and len(b) < need:
        raise Unreadable(f"WebP {tag.decode('latin-1').strip()} header is truncated")
    # The chunk's own size has to cover the fields read below; one declared
    # shorter than that leaves them to be read out of whatever chunk follows.
    if need and int.from_bytes(b[16:20], "little") < need - 20:
        raise Unreadable(f"WebP {tag.decode('latin-1').strip()} chunk is too short "
                         "to state a size")
    if tag == b"VP8X":
        flags = b[20]
        w = int.from_bytes(b[24:27], "little") + 1
        h = int.from_bytes(b[27:30], "little") + 1
        return {"format": "WebP", "width": w, "height": h,
                "alpha": bool(flags & 0x10),
                "colour": "ICC embedded" if flags & 0x20 else "none declared",
                "notes": ["extended"] + (["animated"] if flags & 0x02 else []),
                "orientation": _webp_orientation(b) if flags & 0x08 else None}
    if tag == b"VP8L":
        if b[20] != 0x2F:
            raise Unreadable("WebP lossless frame with no signature byte")
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


def _webp_orientation(b: bytes) -> int | None:
    """The orientation in a VP8X file's EXIF chunk, which may follow the image."""
    i = 12
    while i + 8 <= len(b):
        tag, size = b[i:i + 4], int.from_bytes(b[i + 4:i + 8], "little")
        if tag == b"EXIF":
            return exif_orientation(b[i + 8:i + 8 + size])
        i += 8 + size + (size & 1)
    return None


# --- GIF ---------------------------------------------------------------------

def _gif(b: bytes) -> dict:
    if len(b) < 13:
        raise Unreadable("GIF with no logical screen descriptor")
    w, h = struct.unpack("<HH", b[6:10])
    return {"format": "GIF", "width": w, "height": h, "alpha": _gif_transparent(b),
            "colour": "none declared", "notes": [b[:6].decode("latin-1")]}


def _gif_transparent(b: bytes) -> bool:
    """Whether the picture shows anything through it.

    A graphic control extension's presence is not the answer: an animated GIF
    carries one per frame for the delay alone. Nor is its transparency flag on
    a later frame: an encoder marks unchanged pixels transparent so the frame
    before shows through, and over a first frame that covers the whole canvas
    opaquely, and is never cleared to the background (disposal 2) before the
    last frame, that is still an opaque picture. Anything else that sets the
    flag is counted, since telling more apart would mean decoding the pixels.
    Walked block by block, because the colour tables are raw bytes that can
    contain the extension's introducer by chance.
    """
    W, H = struct.unpack("<HH", b[6:10])
    frames = []                                  # (transparent, disposal, covers)
    gce = (False, 0)
    i = 13 + ((3 << ((b[10] & 7) + 1)) if b[10] & 0x80 else 0)
    while i < len(b):
        if b[i] == 0x21 and i + 1 < len(b):                # extension
            if b[i + 1] == 0xF9 and i + 3 < len(b):
                gce = (bool(b[i + 3] & 1), (b[i + 3] >> 2) & 7)
            i += 2
        elif b[i] == 0x2C and i + 10 < len(b):             # image descriptor
            x, y, w, h = struct.unpack("<HHHH", b[i + 1:i + 9])
            frames.append((*gce, (x, y, w, h) == (0, 0, W, H)))
            gce = (False, 0)
            packed = b[i + 9]
            i += 10 + ((3 << ((packed & 7) + 1)) if packed & 0x80 else 0) + 1
        else:                                              # trailer, or damage
            break
        while i < len(b) and b[i]:                         # data sub-blocks
            i += b[i] + 1
        i += 1
    if not frames:
        return gce[0]
    if frames[0][0]:
        return True
    kept = frames[0][2] and all(d != 2 for _, d, _ in frames[:-1])
    return not kept and any(t for t, _, _ in frames)


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
    try:
        for sig, fn in READERS:
            if raw.startswith(sig):
                out = fn(raw)
                break
        if out is None and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            out = _webp(raw)
    except (struct.error, IndexError) as e:
        # A reader that ran off the end of a cut-short file. That is a fact
        # about the file, and it is reported as one rather than as a traceback.
        raise Unreadable(f"{path.name}: truncated or malformed header ({e})") from e
    if out is None:
        raise Unreadable(f"{path.name}: not a PNG, JPEG, WebP or GIF")
    w, h = out["width"], out["height"]
    if w <= 0 or h <= 0:
        raise Unreadable(f"{path.name}: header states {w}x{h}")
    g = math.gcd(w, h)
    # The size is what the file stores, and what a canvas or a strip is checked
    # against. A viewer honouring Exif shows 5-8 turned a quarter, so a stored
    # 3:2 is a 2:3 picture: a reviewer asking for the shape asked for, and
    # reading only the stored size, would get a confident wrong answer.
    turn = out.pop("orientation", None)
    if turn in range(2, 9):
        dw, dh = (h, w) if turn >= 5 else (w, h)
        dg = math.gcd(dw, dh)
        out.update(orientation=turn, displayed=f"{dw}x{dh}",
                   displayed_ratio=f"{dw // dg}:{dh // dg}")
    out.update(path=str(path), bytes=len(raw),
               sha256=hashlib.sha256(raw).hexdigest()[:16],
               size=f"{w}x{h}", ratio=f"{w // g}:{h // g}",
               megapixels=round(w * h / 1_000_000, 2),
               breaks=sorted(illegal(w, h)))
    return out


def complete(raw: bytes) -> bool:
    """Whether the file reaches its own end marker — PNG's IEND, JPEG's EOI, the
    end the WebP RIFF header declares, GIF's trailer. A header can be whole
    while the rest is still being written, and a header is all `probe` reads."""
    if raw.startswith(PNG_SIG):
        return _png_reaches_iend(raw)
    if raw.startswith(b"\xff\xd8"):
        try:
            scanned = False                  # EOI counts after a scan with data in it
            for m, start, stop, _ in jpeg_segments(raw, through_scans=True):
                scanned = scanned or (m is None and stop > start)
                if m == 0xD9:
                    return scanned
            return False
        except (struct.error, IndexError):
            return False
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return _webp_holds_image(raw)
    if raw[:4] == b"GIF8":
        try:
            return _gif_reaches_trailer(raw)
        except IndexError:
            return False
    return False


# The smallest payload a bitstream chunk can have and still hold a frame: VP8's
# frame tag, start code and dimensions; VP8L's signature byte and dimensions.
# A structural check, not a decoder — enough that a name alone is not pixels.
_WEBP_IMAGE_MIN = {b"VP8 ": 10, b"VP8L": 5}


def _webp_bitstream(kind: bytes, body: bytes) -> bool:
    """A bitstream chunk of at least its smallest size that opens the way its
    format must: VP8L with its 0x2f signature, VP8 with its frame start code."""
    if len(body) < _WEBP_IMAGE_MIN.get(kind, 1 << 32):
        return False
    return body[0] == 0x2F if kind == b"VP8L" else body[3:6] == b"\x9d\x01\x2a"


def _webp_frame(kind: bytes, body: bytes) -> bool:
    """Whether one chunk carries a frame: a bitstream chunk, or an ANMF whose
    nested chunks, after its 16-byte frame header, include one — each nested
    chunk whole, its pad byte included."""
    if kind in _WEBP_IMAGE_MIN:
        return _webp_bitstream(kind, body)
    if kind != b"ANMF":
        return False
    pos = 16
    while pos + 8 <= len(body):
        inner, size = body[pos:pos + 4], struct.unpack("<I", body[pos + 4:pos + 8])[0]
        nxt = pos + 8 + size + (size & 1)
        if nxt > len(body):
            return False
        if _webp_bitstream(inner, body[pos + 8:pos + 8 + size]):
            return True
        pos = nxt
    return False


def _webp_holds_image(raw: bytes) -> bool:
    """The RIFF size the file declares is all there, and the chunks inside it
    include one that carries pixels. A size field still zero, as a writer
    leaves it until the end, declares a file that is not there yet; a VP8X
    chunk alone states a canvas and holds no image."""
    end = 8 + struct.unpack("<I", raw[4:8])[0]
    if end > len(raw):
        return False
    pos, pixels = 12, False
    while pos + 8 <= end:
        kind, size = raw[pos:pos + 4], struct.unpack("<I", raw[pos + 4:pos + 8])[0]
        body = raw[pos + 8:pos + 8 + size]
        pos += 8 + size + (size & 1)         # an odd payload's pad byte is part
        if pos > end:                        # of the file, though not of size
            return False
        pixels = pixels or _webp_frame(kind, body)
    return pixels and pos == end


def _png_reaches_iend(raw: bytes) -> bool:
    """Walked chunk by chunk, so bytes appended after IEND (which strip
    removes) do not hide it, and an IEND-shaped run inside a cut-short chunk
    does not stand in for it. IEND counts only after an IDAT: a header with
    no image data declares a picture that is not in the file."""
    pos, data = len(PNG_SIG), False
    while pos + 12 <= len(raw):
        length, kind = struct.unpack(">I4s", raw[pos:pos + 8])
        pos += 12 + length
        data = data or (kind == b"IDAT" and length > 0)
        if kind == b"IEND":
            return data and pos <= len(raw)
    return False


def _gif_reaches_trailer(raw: bytes) -> bool:
    """Walked block by block to the 0x3B trailer: that byte also turns up
    inside image data, so a file cut short there is not finished. The trailer
    counts after an image block with data in it, not after a header alone."""
    def table(flags: int) -> int:
        return 3 * 2 ** ((flags & 7) + 1) if flags & 0x80 else 0

    def sub_blocks(pos: int) -> int:
        while raw[pos]:
            pos += 1 + raw[pos]
        return pos + 1

    pos, image = 13 + table(raw[10]), False
    while True:
        tag = raw[pos]
        if tag == 0x3B:
            return image
        if tag == 0x21:                      # extension: label, then sub-blocks
            pos = sub_blocks(pos + 2)
        elif tag == 0x2C:                    # image: descriptor, table, LZW size
            data = pos + 10 + table(raw[pos + 9]) + 1
            image = image or raw[data] > 0
            pos = sub_blocks(data)
        else:
            return False


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
    if w <= 0 or h <= 0:
        return None
    aspect, want = w / h, w * h
    # The legal shape nearest this one is the aspect clamped to the ratio
    # limit, measured with the same relative drift the search below uses —
    # one rule, so the cut-off and the search cannot disagree about a shape
    # (a fixed margin did, in both directions, near 3:1 and near 1:3).
    lim = CANVAS["max_ratio"]
    closest = min(max(aspect, 1 / lim), lim)
    if abs(closest - aspect) / aspect > ASPECT_TOLERANCE:
        return None
    inside, outside = [], []
    # The whole grid. A range of scales around the request answered "nothing
    # is legal" for 16x16 and for 100000x100000, and the two heights nearest
    # the aspect per width missed the legal one just under the edge limit.
    # Sixty thousand candidates is still instant.
    grid = range(m, CANVAS["max_edge"] + 1, m)
    for cw in grid:
        for ch in grid:
            if illegal(cw, ch):
                continue
            drift = abs(cw / ch - aspect) / aspect
            (inside if drift <= ASPECT_TOLERANCE else outside).append(
                ((abs(cw * ch - want), drift) if drift <= ASPECT_TOLERANCE
                 else (drift, abs(cw * ch - want)), (cw, ch)))
    pool = inside or outside
    return min(pool)[1] if pool else None


def aspect_of(w: int, h: int) -> str:
    """The reduced `W:H` a size is, which is the only size lever an aspect
    generator has. 1254x1254 and 1024x1024 are the same request to it."""
    g = math.gcd(w, h)
    return f"{w // g}:{h // g}"


def aspect_offered(name: str) -> list[str]:
    gen = ASPECT_GENERATORS.get(name)
    if gen is None:
        raise KeyError(f"{name} is not a generator that takes an aspect; "
                       f"the registry lists {sorted(ASPECT_GENERATORS)}")
    return list(gen["aspects"])


def nearest_aspect(ratio: str, name: str) -> str:
    """The offered aspect closest in shape. Closest is by ratio, not by string:
    a request for 5:4 is answered with 4:3 and not with the first one listed."""
    a, b = (int(x) for x in ratio.split(":"))
    return min(aspect_offered(name),
               key=lambda o: abs(math.log((a / b) / _ratio(o))))


def _ratio(spec: str) -> float:
    a, b = (int(x) for x in spec.split(":"))
    return a / b


# --- output ------------------------------------------------------------------

def render(f: dict) -> str:
    head = (f"{f['path']}\n"
            f"  {f['size']}  {f['ratio']}  {f['megapixels']} MP  "
            f"{f['format']}  {f['bytes']:,} bytes  sha256:{f['sha256']}")
    tail = (f"\n  alpha: {'yes' if f['alpha'] else 'no'}   "
            f"colour: {f['colour']}")
    if f["notes"]:
        tail += f"   {', '.join(f['notes'])}"
    if f.get("orientation"):
        tail += (f"\n  Exif orientation {f['orientation']}: shown as "
                 f"{f['displayed']} ({f['displayed_ratio']}), stored as {f['size']}")
    if f["breaks"]:
        tail += (f"\n  not a legal {CANVAS_GENERATOR} canvas: breaks "
                 + ", ".join(f["breaks"]))
    if f.get("nearest_aspect"):
        tail += (f"\n  {f['generator']} takes an aspect, not a canvas: nearest "
                 f"of its aspects is {f['nearest_aspect']}")
    return head + tail


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("files", nargs="*", type=Path)
    p.add_argument("--json", action="store_true", help="one object per file")
    p.add_argument("--check-size", metavar="WxH",
                   help="ask whether a canvas is legal, without a file")
    p.add_argument("--check-aspect", metavar="W:H",
                   help="ask whether an aspect generator is offered this shape")
    p.add_argument("--generator", default=None,
                   help=f"which generator to ask; aspect: {sorted(ASPECT_GENERATORS)}")
    a = p.parse_args(argv)

    if a.check_aspect:
        if a.generator is None and len(ASPECT_GENERATORS) > 1:
            print(f"--check-aspect needs --generator: the registry declares "
                  f"{sorted(ASPECT_GENERATORS)}, and their lists differ", file=sys.stderr)
            return 2
        name = a.generator or next(iter(ASPECT_GENERATORS), "")
        try:
            offered = aspect_offered(name)
            ratio = a.check_aspect if ":" in a.check_aspect else ""
            w, h = (int(x) for x in ratio.split(":"))
            if not (0 < w <= MAX_EDGE and 0 < h <= MAX_EDGE):
                raise ValueError(ratio)
        except (KeyError, ValueError) as e:
            print(e if isinstance(e, KeyError) else
                  f"not an aspect: {a.check_aspect!r} (want W:H)", file=sys.stderr)
            return 2
        want = aspect_of(w, h)
        ok = want in offered
        near = None if ok else nearest_aspect(want, name)
        if a.json:
            print(json.dumps({"aspect": want, "generator": name, "offered": ok,
                              "nearest_offered": near, "choices": offered}))
        elif ok:
            print(f"{want} is one of the {len(offered)} aspects {name} offers")
        else:
            print(f"{name} does not offer {want}; nearest offered is {near}. "
                  f"It takes no pixel size, so this is the whole lever")
        return 0 if ok else 1

    if a.check_size:
        if a.generator not in (None, CANVAS_GENERATOR):
            print(f"--check-size answers for {CANVAS_GENERATOR}'s canvas; " + (
                  f"{a.generator} takes no pixel size (ask --check-aspect)"
                  if a.generator in GENERATORS else
                  f"{a.generator} is not a generator the registry lists"), file=sys.stderr)
            return 2
        try:
            w, h = (int(x) for x in a.check_size.lower().split("x"))
            if not (0 < w <= MAX_EDGE and 0 < h <= MAX_EDGE):
                raise ValueError(a.check_size)
        except ValueError:
            print(f"not a size: {a.check_size!r} (want WxH, each edge 1..{MAX_EDGE})",
                  file=sys.stderr)
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
    # Asked about a file, --generator says whose rules it is judged by. An
    # aspect generator has no canvas to break; a name nobody declared is an
    # input error, as it is to --check-size, not a quiet answer for codex.
    named = {n for n, g in GENERATORS.items() if isinstance(g, dict)}
    if a.generator is not None and a.generator not in named:
        print(f"{a.generator} is not a generator the registry lists: "
              f"{sorted(named)}", file=sys.stderr)
        return 2
    # A name that is not valid UTF-8 is still a name to report, not a traceback.
    with contextlib.suppress(AttributeError, ValueError):
        sys.stdout.reconfigure(errors="backslashreplace")

    facts, bad = [], False
    for f in a.files:
        try:
            facts.append(probe(f))
            if a.generator in ASPECT_GENERATORS:
                facts[-1].update(breaks=[], generator=a.generator,
                                 nearest_aspect=nearest_aspect(facts[-1]["ratio"],
                                                               a.generator))
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
