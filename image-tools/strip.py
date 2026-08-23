#!/usr/bin/env python3
"""Remove what should not ship from a generated image, and nothing else.

`image-deliver/reference/colour-and-metadata.md` fixes the policy: strip camera
fields, location, timestamps, comments and embedded thumbnails; keep the colour
profile, the alpha channel, and any provenance block the project decided to
carry. This applies it.

    strip.py hero.png                      # what would go, and what stays
    strip.py hero.png --out web/hero.png
    strip.py assets/*.png --in-place

**Generation parameters can be inside the file.** Several image generators write
their prompt, model and settings into PNG text chunks or XMP, so an unstripped
asset can publish the wording that made it and sometimes a local path. That is
the reason the default is to name what stays rather than what goes: a block
nobody here has heard of is removed rather than shipped.

Not every generator does it. The one this set is built around was measured and
does not — its PNGs carry an `eXIf` block holding colour space and pixel
dimensions and nothing else. The default still strips it, because "this build
of this tool wrote nothing sensitive today" is not a property anyone can rely
on, and because the information that *is* worth keeping belongs in the recipe
beside the file (`recipe.py`), which is deliberate and version-controlled.

It edits containers, never pixels: chunks and segments are copied or dropped
byte for byte, so nothing is re-encoded and no generation of lossy damage is
added. It refuses rather than guesses — an Exif orientation that is not upright
stops the run, because applying a rotation would mean decoding the image, and
dropping the flag without applying it turns the picture ninety degrees somewhere
downstream.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True
import imgfacts                                            # noqa: E402

# --- policy ------------------------------------------------------------------
#
# One table, read by every format handler below. `keep` survives by default,
# `colour` survives unless --drop-profile, `credentials` survives unless
# --drop-credentials, and everything not named is stripped. Naming what stays
# rather than what goes means a metadata block nobody has heard of is removed
# by default instead of shipped by default.

PNG_STRUCTURE = {"IHDR", "PLTE", "IDAT", "IEND", "acTL", "fcTL", "fdAT"}
PNG_COLOUR = {"iCCP", "sRGB", "gAMA", "cHRM", "sBIT"}
PNG_RENDER = {"tRNS", "bKGD", "pHYs"}
PNG_CREDENTIALS = {"caBX"}                    # C2PA content credentials

JPEG_CREDENTIALS = {0xEB}                     # APP11, JUMBF
JPEG_KEEP_APP = {0xE0, 0xEE}                  # JFIF density, Adobe colour transform
EXIF_SIG = b"Exif\x00\x00"

WEBP_STRUCTURE = {b"VP8 ", b"VP8L", b"VP8X", b"ALPH", b"ANIM", b"ANMF"}
WEBP_COLOUR = {b"ICCP"}
VP8X_EXIF, VP8X_XMP = 0x08, 0x04


class Refused(Exception):
    """A strip that would change the picture, not just what travels with it."""


def _orientation(block: bytes) -> int | None:
    """The Exif orientation tag, or None when the block does not state one.

    The `Exif\x00\x00` prefix is optional here on purpose. A JPEG APP1 always
    carries it, a PNG `eXIf` chunk holds bare TIFF, and WebP encoders differ —
    so the caller hands over whatever the container held and this decides. An
    earlier version had each caller prepend the prefix, which for the WebP
    encoders that already write one produced `ExifExif\x00\x00...`, no
    recognisable TIFF header, no orientation found, and a sideways picture
    stripped without a word.
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
            if tag == 0x0112 and typ == 3 and n == 1:
                return struct.unpack(end + "H", b[e + 8:e + 10])[0]
    except (struct.error, IndexError):
        return None
    return None


# --- PNG ---------------------------------------------------------------------

def _strip_png(raw: bytes, opt) -> tuple[bytes, list[str]]:
    out, dropped, i = bytearray(imgfacts.PNG_SIG), [], 8
    while i + 8 <= len(raw):
        size, tag = struct.unpack(">I4s", raw[i:i + 8])
        name = tag.decode("latin-1")
        body = raw[i + 8:i + 8 + size]
        whole = raw[i:i + 12 + size]
        keep = (name in PNG_STRUCTURE or name in PNG_RENDER
                or (name in PNG_COLOUR and not opt.drop_profile)
                or (name in PNG_CREDENTIALS and not opt.drop_credentials))
        if name == "eXIf":
            o = _orientation(body)
            if o not in (None, 1) and not opt.orientation_is_applied:
                raise Refused(f"Exif orientation is {o}, not upright. Rotate the "
                              "pixels first, then pass --orientation-is-applied")
        if keep:
            out += whole
        else:
            dropped.append(f"{name} ({size:,} bytes)")
        i += 12 + size
        if name == "IEND":
            break
    return bytes(out), dropped


# --- JPEG --------------------------------------------------------------------

def _strip_jpeg(raw: bytes, opt) -> tuple[bytes, list[str]]:
    out, dropped = bytearray(b"\xff\xd8"), []
    for marker, start, end, body in imgfacts.jpeg_segments(raw):
        if marker == 0xDA:                     # scan; the rest is entropy data
            out += raw[start:]
            break
        whole = raw[start:end]
        if body is None:                       # standalone marker, no payload
            out += whole
            continue
        if marker == 0xE1 and body.startswith(EXIF_SIG):
            o = _orientation(body)
            if o not in (None, 1) and not opt.orientation_is_applied:
                raise Refused(f"Exif orientation is {o}, not upright. Rotate the "
                              "pixels first, then pass --orientation-is-applied")
        if marker == 0xFE:                     # COM is a comment; it goes
            keep = False
        elif not 0xE0 <= marker <= 0xEF:       # everything structural stays
            keep = True
        elif marker == 0xE2 and body.startswith(b"ICC_PROFILE\x00"):
            keep = not opt.drop_profile
        elif marker in JPEG_CREDENTIALS:
            keep = not opt.drop_credentials
        else:
            keep = marker in JPEG_KEEP_APP
        if keep:
            out += whole
        else:
            label = "COM" if marker == 0xFE else f"APP{marker - 0xE0}"
            hint = body[:12].split(b"\x00")[0].decode("latin-1", "replace")
            dropped.append(f"{label} {hint!r} ({len(body) + 2:,} bytes)")
    return bytes(out), dropped


# --- WebP --------------------------------------------------------------------

def _strip_webp(raw: bytes, opt) -> tuple[bytes, list[str]]:
    body, dropped, i = bytearray(b"WEBP"), [], 12
    while i + 8 <= len(raw):
        tag = raw[i:i + 4]
        size = struct.unpack("<I", raw[i + 4:i + 8])[0]
        padded = size + (size & 1)
        whole = raw[i:i + 8 + padded]
        keep = (tag in WEBP_STRUCTURE
                or (tag in WEBP_COLOUR and not opt.drop_profile))
        if tag == b"EXIF":
            o = _orientation(raw[i + 8:i + 8 + size])
            if o not in (None, 1) and not opt.orientation_is_applied:
                raise Refused(f"Exif orientation is {o}, not upright. Rotate the "
                              "pixels first, then pass --orientation-is-applied")
        if keep:
            if tag == b"VP8X":                 # the flags must stop advertising
                head = bytearray(whole)        # blocks that are no longer there
                head[8] &= ~(VP8X_EXIF | VP8X_XMP)
                if opt.drop_profile:
                    head[8] &= ~0x20
                whole = bytes(head)
            body += whole
        else:
            dropped.append(f"{tag.decode('latin-1').strip()} ({size:,} bytes)")
        i += 8 + padded
    return b"RIFF" + struct.pack("<I", len(body)) + bytes(body), dropped


HANDLERS = {"PNG": _strip_png, "JPEG": _strip_jpeg, "WebP": _strip_webp}


# --- driver ------------------------------------------------------------------

def strip(path: Path, opt) -> tuple[bytes, list[str], dict]:
    before = imgfacts.probe(path)
    fn = HANDLERS.get(before["format"])
    if fn is None:
        raise Refused(f"{before['format']} is not handled; nothing was changed")
    out, dropped = fn(path.read_bytes(), opt)

    # The tool's own output gets the same treatment as anything else here: read
    # off the result, never assumed from the operation. From memory, because a
    # run with neither --out nor --in-place is a report, and a report that needs
    # a writable directory beside the input is not one.
    after = imgfacts.probe_bytes(out, f"{path} (stripped)")
    for k in ("format", "size", "alpha"):
        if after[k] != before[k]:
            raise Refused(f"stripping changed {k} from {before[k]!r} to "
                          f"{after[k]!r}; the file was not written")
    if not opt.drop_profile and after["colour"] != before["colour"]:
        raise Refused(f"stripping changed the colour profile from "
                      f"{before['colour']!r} to {after['colour']!r}; "
                      "the file was not written")
    return out, dropped, before


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--out", type=Path, help="one input only; default is a report")
    p.add_argument("--in-place", action="store_true")
    p.add_argument("--drop-profile", action="store_true",
                   help="also remove the colour profile. Read the page first")
    p.add_argument("--drop-credentials", action="store_true",
                   help="also remove content credentials. A project decision")
    p.add_argument("--orientation-is-applied", action="store_true",
                   help="the pixels are already upright; the flag may go")
    a = p.parse_args(argv)
    if a.out and (len(a.files) > 1 or a.in_place):
        p.error("--out takes one input and does not combine with --in-place")

    failed = False
    for f in a.files:
        try:
            out, dropped, before = strip(f, a)
        except (Refused, imgfacts.Unreadable, OSError) as e:
            print(f"{f}: {e}", file=sys.stderr)
            failed = True
            continue
        saved = before["bytes"] - len(out)
        verb = "would remove" if not (a.out or a.in_place) else "removed"
        print(f"{f}  {before['size']}  {before['bytes']:,} bytes")
        for d in dropped:
            print(f"  {verb} {d}")
        if not dropped:
            print("  nothing to remove")
        print(f"  keeps: {before['colour']}, "
              f"alpha {'yes' if before['alpha'] else 'no'}"
              + (f"   -{saved:,} bytes" if saved else ""))
        dest = a.out or (f if a.in_place else None)
        if dest:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(out)
            print(f"  wrote {dest}  {len(out):,} bytes")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
