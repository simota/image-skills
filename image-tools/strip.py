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
import os
import struct
import sys
import tempfile
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
# cICP, mDCV and cLLI are how a PNG states an HDR colour space and its mastering
# display; dropping them changes how the picture is shown, not what travels with it.
PNG_COLOUR = {"iCCP", "sRGB", "gAMA", "cHRM", "sBIT", "cICP", "mDCV", "cLLI"}
PNG_RENDER = {"tRNS", "bKGD", "pHYs"}
PNG_CREDENTIALS = {"caBX"}                    # C2PA content credentials

JPEG_CREDENTIALS = {0xEB}                     # APP11, JUMBF
# Kept by marker *and* signature: APP0 also carries JFXX thumbnails, and an
# embedded thumbnail is on the list of what goes.
JPEG_KEEP_APP = {0xE0: b"JFIF\x00",          # density
                 0xEE: b"Adobe"}               # colour transform
EXIF_SIG = b"Exif\x00\x00"
JFIF_HEAD = 14                                # "JFIF\0", version, units, density, thumb w/h

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
    out, dropped, i, ended = bytearray(imgfacts.PNG_SIG), [], 8, False
    while i + 8 <= len(raw):
        size, tag = struct.unpack(">I4s", raw[i:i + 8])
        name = tag.decode("latin-1")
        if i + 12 + size > len(raw):
            raise Refused(f"PNG is truncated inside {name}; nothing was changed")
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
            dropped.append((name, len(whole)))
        i += 12 + size
        if name == "IEND":
            ended = True
            break
    if not ended:
        raise Refused("PNG has no IEND, so it is truncated; nothing was changed")
    if i < len(raw):
        dropped.append(("data after IEND", len(raw) - i))
    return bytes(out), dropped


# --- JPEG --------------------------------------------------------------------

def _strip_jpeg(raw: bytes, opt) -> tuple[bytes, list[str]]:
    # `pos` is how far the input has been accounted for. Bytes the segment walk
    # skips are reported rather than lost quietly, and a file that ends before
    # EOI is refused as PNG's missing IEND is: half a picture is not stripped.
    out, dropped, tail, pos = bytearray(b"\xff\xd8"), [], None, 2
    for marker, start, end, body in imgfacts.jpeg_segments(raw, through_scans=True):
        if end > len(raw):
            raise Refused("JPEG is truncated inside a segment; nothing was changed")
        if start > pos:
            dropped.append(("stray bytes between segments", start - pos))
        pos = end
        whole = raw[start:end]
        if body is None:                       # entropy data, or a standalone marker
            out += whole
            if marker == 0xD9:
                tail = end
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
            keep = body.startswith(JPEG_KEEP_APP.get(marker, b"\x00unmatched"))
        if keep and marker == 0xE0 and len(body) > JFIF_HEAD and body[12:14] != b"\x00\x00":
            # JFIF carries an optional thumbnail after its 14-byte header. The
            # header stays, the thumbnail goes, and the segment says so.
            head = body[:12] + b"\x00\x00"
            out += b"\xff\xe0" + struct.pack(">H", len(head) + 2) + head
            dropped.append(("JFIF thumbnail", len(whole) - len(head) - 4))
        elif keep:
            out += whole
        else:
            label = "COM" if marker == 0xFE else f"APP{marker - 0xE0}"
            hint = body[:12].split(b"\x00")[0].decode("latin-1", "replace")
            dropped.append((f"{label} {hint!r}", end - start))
    if tail is None:
        raise Refused("JPEG has no EOI, so it is truncated; nothing was changed")
    if tail < len(raw):
        # Not this image: an appended second picture (a motion photo, an MPF
        # preview) carries its own Exif and location, and ships them if kept.
        dropped.append(("data after EOI", len(raw) - tail))
    return bytes(out), dropped


# --- WebP --------------------------------------------------------------------

def _strip_webp(raw: bytes, opt) -> tuple[bytes, list[str]]:
    body, dropped, i = bytearray(b"WEBP"), [], 12
    # The RIFF header says where the file ends. Bytes past it are not chunks,
    # and reading them as one called a file with a trailer "truncated".
    end = 8 + struct.unpack("<I", raw[4:8])[0]
    if end > len(raw):
        raise Refused(f"WebP's RIFF header says {end:,} bytes and the file has "
                      f"{len(raw):,}; it is truncated, and nothing was changed")
    flags_note = None
    while i + 8 <= end:
        tag = raw[i:i + 4]
        size = struct.unpack("<I", raw[i + 4:i + 8])[0]
        padded = size + (size & 1)
        if i + 8 + size > end:
            raise Refused(f"WebP is truncated inside {tag!r}; nothing was changed")
        # Never past the RIFF end: a final chunk missing its pad stays missing
        # (this edits containers, never repairs them), and the byte after it is
        # the trailer's, not a pad to copy along.
        whole = raw[i:min(i + 8 + padded, end)]
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
                if head[8] != whole[8]:
                    flags_note = (whole[8], head[8])
                whole = bytes(head)
            body += whole
        else:
            dropped.append((tag.decode("latin-1").strip(), len(whole)))
        i += 8 + padded
    # A flag cleared along with the chunk it advertised is that chunk's
    # removal, already reported; one advertising a chunk that was never there
    # is a change of its own, and says so.
    gone = {d for d, _ in dropped}
    if flags_note and not gone & {"EXIF", "XMP", "ICCP"}:
        dropped.append((f"VP8X flags {flags_note[0]:#04x} -> {flags_note[1]:#04x}, "
                        "which advertised blocks the file does not have", 0))
    if i < end:                                # reported independently of a
        dropped.append(("residue too short to be a chunk", end - i))   # trailer
    if end < len(raw):
        dropped.append(("data after RIFF", len(raw) - end))
    return b"RIFF" + struct.pack("<I", len(body)) + bytes(body), dropped


HANDLERS = {"PNG": _strip_png, "JPEG": _strip_jpeg, "WebP": _strip_webp}


# --- driver ------------------------------------------------------------------

def strip(path: Path, opt) -> tuple[bytes, list[str], dict]:
    before = imgfacts.probe(path)
    fn = HANDLERS.get(before["format"])
    if fn is None:
        raise Refused(f"{before['format']} is not handled; nothing was changed")
    raw = path.read_bytes()
    out, ledger = fn(raw, opt)
    # The report is a ledger and has to balance: what it names, byte for byte,
    # is what the file lost. Each handler counts what it actually dropped, and
    # a mismatch is refused rather than written under a report that is wrong —
    # four reviews in a row found a new way for a per-branch count to drift.
    named = sum(n for _, n in ledger)
    if named != len(raw) - len(out):
        raise Refused(f"the report accounts for {named:,} bytes and the file "
                      f"lost {len(raw) - len(out):,}; nothing was written")
    dropped = [f"{what} ({n:,} bytes)" for what, n in ledger]

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


def _write_atomically(dest: Path, data: bytes) -> None:
    """Replace `dest` whole or not at all. `--in-place` overwrites the only copy
    of an asset, and an interrupted plain write leaves half of one.

    A symlink is followed, not replaced: renaming over the link would leave the
    image it points to unstripped while reporting it done. The same holds for a
    file with other hard links, and a directory that refuses new files has no
    room for the temporary copy — both are written through the existing inode
    instead, which also keeps its owner, extended attributes and ACLs.

    That path cannot be atomic, so before the inode is touched the original is
    written durably to the system temporary directory; if that copy cannot be
    made, nothing is changed. A failed write is then undone from memory —
    stripping only shrinks a file, so neither step needs new space on an
    ordinary filesystem — and the copy is removed once the file is whole again.
    If the restore fails too, the copy stays and the error names it: a
    half-written only copy with no original anywhere is never the outcome."""
    dest = dest.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and (dest.stat().st_nlink > 1
                          or not os.access(dest.parent, os.W_OK)):
        original = dest.read_bytes()
        keep, retain = None, False
        try:                                 # the copy's whole lifetime: removed
            try:                             # on every way out but one
                fd, keep = tempfile.mkstemp(prefix=f"{dest.name}.original.")
                with os.fdopen(fd, "wb") as k:
                    k.write(original)
                    k.flush()
                    os.fsync(k.fileno())
            except OSError as e:
                raise OSError(e.errno, f"could not save a recovery copy of {dest} "
                              f"({e.strerror}); nothing was changed") from None
            with open(dest, "r+b") as f:
                try:
                    _overwrite(f, data)
                except BaseException as failed:  # an interrupt too: the finally
                    try:                         # below must not delete the copy
                        _overwrite(f, original)  # of a half-written file
                    except BaseException:
                        retain = True            # the one way out that keeps it
                        where = f"{dest} may be damaged, original saved to {keep}"
                        if not isinstance(failed, OSError):
                            # The interrupt is what the caller is waiting for,
                            # so it propagates — after the one fact that makes
                            # the damage recoverable has been said.
                            print(f"strip.py: {where}", file=sys.stderr)
                            raise failed from None
                        raise OSError(failed.errno, f"{failed.strerror}; {where}") from None
                    if not isinstance(failed, OSError):
                        raise
                    raise OSError(failed.errno, f"{failed.strerror}; {dest} was "
                                  "restored unchanged") from None
        finally:
            if keep and not retain:
                Path(keep).unlink(missing_ok=True)
        return
    fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if dest.exists():
            st = dest.stat()
            os.chmod(tmp, st.st_mode & 0o7777)
            try:                               # keep the owner where allowed
                os.chown(tmp, st.st_uid, st.st_gid)
            except OSError:
                pass
        else:
            os.chmod(tmp, 0o666 & ~_umask())
        os.replace(tmp, dest)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _overwrite(f, data: bytes) -> None:
    f.seek(0)
    f.write(data)
    f.truncate()
    f.flush()
    os.fsync(f.fileno())


def _umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask


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
        except (Refused, imgfacts.Unreadable, OSError, struct.error, IndexError) as e:
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
            try:
                _write_atomically(dest, out)
            except OSError as e:
                print(f"{f}: could not write {dest}: {e}", file=sys.stderr)
                failed = True
                continue
            print(f"  wrote {dest}  {len(out):,} bytes")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
