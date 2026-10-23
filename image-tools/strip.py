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
import contextlib
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
# Kept only when it is JUMBF: after the common identifier, the En and Z
# fields, every segment repeats the box header, whose type is `jumb`. Any
# other APP11 — another JPEG XT box, or private data that happens to open
# with "JP" — is a block nobody here has named, and those go.
JUMBF_CI = b"JP"


def _is_jumbf(body: bytes) -> bool:
    return body.startswith(JUMBF_CI) and body[12:16] == b"jumb"
# Kept by marker *and* signature: APP0 also carries JFXX thumbnails, and an
# embedded thumbnail is on the list of what goes.
JPEG_KEEP_APP = {0xE0: b"JFIF\x00",          # density
                 0xEE: b"Adobe"}               # colour transform
EXIF_SIG = imgfacts.EXIF_SIG
JFIF_HEAD = 14                                # "JFIF\0", version, units, density, thumb w/h

WEBP_STRUCTURE = {b"VP8 ", b"VP8L", b"VP8X", b"ALPH", b"ANIM", b"ANMF"}
WEBP_COLOUR = {b"ICCP"}
WEBP_CREDENTIALS = {b"C2PA"}                  # where C2PA embeds in a RIFF file
VP8X_EXIF, VP8X_XMP = 0x08, 0x04


class Refused(Exception):
    """A strip that would change the picture, not just what travels with it."""


def _refuse_rotation(block: bytes, opt) -> None:
    """Refuse when the block turns the picture. Only 2-8 do: 1 is upright, and
    0 or anything past 8 is no orientation at all, which readers show upright."""
    o = imgfacts.exif_orientation(block)
    if o in range(2, 9) and not opt.orientation_is_applied:
        raise Refused(f"Exif orientation is {o}, not upright. Rotate the "
                      "pixels first, then pass --orientation-is-applied")


# An HDR gain map: the primary JPEG names it in XMP (`hdrgm`) or an ISO 21496-1
# APP2, and the map itself is a second JPEG after EOI, found through MPF. All
# of that is removed here, and an HDR display then shows the SDR base alone —
# a change to how the picture is shown, as dropping a PNG's cICP would be.
GAIN_MAP_SIGNS = (b"http://ns.adobe.com/hdr-gain-map/1.0/", b"urn:iso:std:iso:ts:21496:-1")


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
            _refuse_rotation(body, opt)
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
    scanned = gain_named = secondary = False
    for marker, start, end, body in imgfacts.jpeg_segments(raw, through_scans=True):
        if end > len(raw):
            raise Refused("JPEG is truncated inside a segment; nothing was changed")
        if start > pos:
            if scanned:
                # Once a scan has begun, bytes the walk could not place are
                # most likely pixels it misread; dropping them would edit the
                # picture, which this never does.
                raise Refused(f"{start - pos} bytes after a scan began could not be "
                              "placed in any segment; nothing was changed")
            dropped.append(("stray bytes between segments", start - pos))
        scanned = scanned or marker == 0xDA
        pos = end
        whole = raw[start:end]
        if body is None:                       # entropy data, or a standalone marker
            out += whole
            if marker == 0xD9:
                tail = end
            continue
        if marker == 0xE1 and body.startswith(EXIF_SIG):
            _refuse_rotation(body, opt)
        if marker in (0xE1, 0xE2) and any(sign in body for sign in GAIN_MAP_SIGNS):
            gain_named = True
        if marker == 0xE2 and body.startswith(b"MPF\x00"):
            secondary = True
        if marker == 0xFE:                     # COM is a comment; it goes
            keep = False
        elif not 0xE0 <= marker <= 0xEF:       # everything structural stays
            keep = True
        elif marker == 0xE2 and body.startswith(b"ICC_PROFILE\x00"):
            keep = not opt.drop_profile
        elif marker in JPEG_CREDENTIALS:
            keep = _is_jumbf(body) and not opt.drop_credentials
        else:
            keep = body.startswith(JPEG_KEEP_APP.get(marker, b"\x00unmatched"))
        if keep and marker == 0xE0 and len(body) > JFIF_HEAD:
            # JFIF carries an optional thumbnail after its 14-byte header. The
            # header stays, the thumbnail goes, and the segment says so. Bytes
            # there under a 0x0 thumbnail go too: the header does not name them.
            head = body[:12] + b"\x00\x00"
            out += b"\xff\xe0" + struct.pack(">H", len(head) + 2) + head
            what = ("JFIF thumbnail" if body[12:14] != b"\x00\x00"
                    else "bytes after the JFIF header")
            dropped.append((what, len(whole) - len(head) - 4))
        elif keep:
            out += whole
        else:
            label = "COM" if marker == 0xFE else f"APP{marker - 0xE0}"
            hint = body[:12].split(b"\x00")[0].decode("latin-1", "replace")
            dropped.append((f"{label} {hint!r}", end - start))
    if tail is None:
        raise Refused("JPEG has no EOI, so it is truncated; nothing was changed")
    # Named is not carried: an editor that copied the XMP across and dropped
    # the second image left nothing to lose. The map is there when an image is.
    if gain_named and (secondary or tail < len(raw)) \
            and not getattr(opt, "drop_gain_map", False):
        raise Refused("this JPEG carries an HDR gain map, which stripping "
                      "removes: an HDR display would show the SDR base alone. "
                      "Pass --drop-gain-map if that is the decision")
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
                or (tag in WEBP_COLOUR and not opt.drop_profile)
                or (tag in WEBP_CREDENTIALS and not opt.drop_credentials))
        if tag == b"EXIF":
            _refuse_rotation(raw[i + 8:i + 8 + size], opt)
        if keep and tag == b"ANMF":
            whole, gone = _frame(whole, size)
            dropped += gone
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


# What a frame of an animated WebP may hold after its 16-byte header. The spec
# lets unknown chunks in there too, and naming what stays holds one level down.
ANMF_FRAME = {b"ALPH", b"VP8 ", b"VP8L"}
ANMF_HEAD = 16


def _frame(whole: bytes, size: int) -> tuple[bytes, list]:
    """One ANMF chunk — `whole`, header and any pad byte included — rebuilt with
    only its frame's image chunks, and the ledger entries for what it lost.
    With nothing to lose it is returned exactly as read, pad byte and all."""
    data = whole[8:8 + size]
    if len(data) < ANMF_HEAD:
        raise Refused("WebP has an ANMF frame shorter than its header; nothing was changed")
    kept, gone, j = bytearray(data[:ANMF_HEAD]), [], ANMF_HEAD
    while j < len(data):
        if j + 8 > len(data):
            raise Refused("WebP has an ANMF frame that ends inside a chunk header; "
                          "nothing was changed")
        tag = data[j:j + 4]
        size = struct.unpack("<I", data[j + 4:j + 8])[0]
        if j + 8 + size > len(data):
            raise Refused(f"WebP is truncated inside {tag!r} in an ANMF frame; "
                          "nothing was changed")
        sub = data[j:min(j + 8 + size + (size & 1), len(data))]
        if tag in ANMF_FRAME:
            kept += sub
        else:
            gone.append(f"{tag.decode('latin-1').strip()} in an ANMF frame")
        j += len(sub)
    if not gone:
        return whole, []
    rebuilt = b"ANMF" + struct.pack("<I", len(kept)) + bytes(kept) + b"\0" * (len(kept) & 1)
    # One entry carries the whole difference, pad bytes included, so the
    # ledger still balances against what the file lost.
    return rebuilt, [(", ".join(gone), len(whole) - len(rebuilt))]


HANDLERS = {"PNG": _strip_png, "JPEG": _strip_jpeg, "WebP": _strip_webp}


# --- driver ------------------------------------------------------------------

def strip(path: Path, opt) -> tuple[bytes, list[str], dict]:
    # Read once: the facts, the strip and the in-place check below all have to
    # be about the same bytes, and a second read is a second version.
    raw = path.read_bytes()
    before = imgfacts.probe_bytes(raw, str(path))
    before["raw"] = raw                       # what an in-place write may replace
    fn = HANDLERS.get(before["format"])
    if fn is None:
        raise Refused(f"{before['format']} is not handled; nothing was changed")
    out, ledger = fn(raw, opt)
    # A content credential's hard binding is a hash over every byte outside its
    # own manifest, so keeping one while anything else changes ships a
    # credential that every validator reads as tampered. Told nothing, this
    # keeps the credential and the file whole rather than choosing for the
    # project which of the two it can do without.
    if out != raw and not opt.drop_credentials:
        unsigned, _ = fn(raw, _Without(opt))
        if unsigned != out:
            raise Refused("this file carries a content credential whose signature "
                          "covers every byte: stripping anything else would make it "
                          "read as tampered. Strip before signing, or pass "
                          "--drop-credentials and sign the result again; nothing was changed")
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


class _Without:
    """`opt`, with credentials dropped: what the strip would be without them."""

    def __init__(self, opt):
        self.__dict__.update(vars(opt))
        self.drop_credentials = True


class Changed(OSError):
    """The file is no longer the bytes that were stripped."""


def _unchanged(dest: Path, expect: bytes | None, current: bytes | None = None) -> None:
    if expect is not None and (dest.read_bytes() if current is None else current) != expect:
        raise Changed(f"{dest} changed after it was read; the newer version was "
                      "kept and nothing was written")


def _write_atomically(dest: Path, data: bytes, expect: bytes | None = None) -> None:
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
    half-written only copy with no original anywhere is never the outcome.

    With `expect` — an in-place strip — the file must still be the bytes that
    were stripped: another writer's change is kept and this write refused,
    rather than overwritten with a stripped copy of the version before it. The
    check is made immediately before the file is touched; a writer landing in
    the instant between that check and the write is not caught."""
    dest = dest.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and (dest.stat().st_nlink > 1
                          or not os.access(dest.parent, os.W_OK)):
        original = dest.read_bytes()
        _unchanged(dest, expect, original)
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
                    except BaseException as again:
                        retain = True            # the one way out that keeps it
                        where = f"{dest} may be damaged, original saved to {keep}"
                        if not isinstance(again, Exception):
                            # Interrupted while restoring: that interrupt wins,
                            # and is not turned into an error main() continues past.
                            print(f"strip.py: {where}", file=sys.stderr)
                            raise
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
                try:
                    Path(keep).unlink(missing_ok=True)
                except OSError as e:             # never replaces what is in flight
                    print(f"strip.py: could not remove the recovery copy {keep}: "
                          f"{e.strerror}", file=sys.stderr)
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
        _unchanged(dest, expect)
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
    p.add_argument("--out", help="the output file, for one input only; "
                   "default is a report")
    p.add_argument("--in-place", action="store_true")
    p.add_argument("--drop-profile", action="store_true",
                   help="also remove the colour profile. Read the page first")
    p.add_argument("--drop-credentials", action="store_true",
                   help="also remove content credentials. A project decision")
    p.add_argument("--orientation-is-applied", action="store_true",
                   help="the pixels are already upright; the flag may go")
    p.add_argument("--drop-gain-map", action="store_true",
                   help="an HDR JPEG may lose its gain map and show as SDR")
    a = p.parse_args(argv)
    if a.out and (len(a.files) > 1 or a.in_place):
        p.error("--out takes one input and does not combine with --in-place")
    # Path() drops a trailing slash, so `--out web/` would become a file named
    # web, and an existing directory would fail only after the report said
    # every block was removed.
    if a.out is not None and (a.out.endswith(("/", os.sep)) or Path(a.out).is_dir()):
        p.error(f"--out names the output file, not a directory: {a.out}")
    a.out = Path(a.out) if a.out is not None else None
    # A file name that is not valid UTF-8 is still a name to report, not a
    # traceback; stderr already escapes it, and stdout is made to as well.
    with contextlib.suppress(AttributeError, ValueError):
        sys.stdout.reconfigure(errors="backslashreplace")

    failed = False
    for f in a.files:
        try:
            out, dropped, before = strip(f, a)
        except (Refused, imgfacts.Unreadable, OSError, struct.error, IndexError) as e:
            print(f"{f}: {e}", file=sys.stderr)
            failed = True
            continue
        saved = before["bytes"] - len(out)
        dest = a.out or (f if a.in_place else None)
        # A file with nothing to remove is not rewritten in place: delivering a
        # file is no reason to rewrite it, and a read-only one stays readable.
        same = a.in_place and out == before["raw"]
        wrote = False
        if dest and not same:
            try:
                _write_atomically(dest, out, expect=before["raw"] if a.in_place else None)
                wrote = True
            except OSError as e:
                print(f"{f}: could not write {dest}: {e}", file=sys.stderr)
                failed = True
        # Said once the write is settled: a run that failed to write removed
        # nothing, whatever it would have.
        verb = "removed" if wrote else "would remove"
        print(f"{f}  {before['size']}  {before['bytes']:,} bytes")
        for d in dropped:
            print(f"  {verb} {d}")
        if not dropped:
            print("  nothing to remove")
        # Read off the result, like everything else here: --drop-profile
        # leaves no profile to keep, whatever the input declared.
        print(f"  keeps: {imgfacts.probe_bytes(out, str(f))['colour']}, "
              f"alpha {'yes' if before['alpha'] else 'no'}"
              + (f"   -{saved:,} bytes" if saved else ""))
        if wrote:
            print(f"  wrote {dest}  {len(out):,} bytes")
        elif same:
            print(f"  left {dest} as it was")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
