#!/usr/bin/env python3
"""Exercise the asset catalogue through the same CLI the delivery skill runs.

PNG fixtures are decodable. JPEG and WebP fixtures test container facts, not
pixel decoding; a catalogue must not claim that header checks viewed pixels.
"""
from __future__ import annotations

import base64
import contextlib
import io
import json
import os
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import quote, unquote

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True
from test_tools import exif, jpeg_with, png, srgb_chunk, webp_vp8l


TOOL = Path(__file__).resolve().with_name("catalog.py")


class Links(HTMLParser):
    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.images: list[dict] = []
        self.anchors: list[dict] = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.images.append(dict(attrs))
        elif tag == "a":
            self.anchors.append(dict(attrs))


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.assets = self.root / "assets"
        self.assets.mkdir()
        self.out = self.root / "reports" / "asset-catalog.html"

    def image(self, name="hero.png", raw=None):
        path = self.assets / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png(16, 8) if raw is None else raw)
        return path

    def recipe(self, image, **changes):
        record = {
            "engine": "recorded invocation",
            "model": "unreported",
            "prompt": "PRIVATE PROMPT: do not copy this into the catalogue",
            "excluded": "none",
            "size": {"asked": "16x8", "on_disk": "16x8"},
            "inputs": [],
            "output": {"generated": "/generator/source.png", "placed": str(image)},
            "note": "IRREPRODUCIBLE — exact regeneration not established",
        }
        record.update(changes)
        side = image.with_name(image.name + ".recipe.yaml")
        side.write_text(yaml.safe_dump(record, allow_unicode=True), encoding="utf-8")
        return side

    def run_catalog(self, *, output=None, format="html", extra=(), directory=None):
        return subprocess.run(
            [sys.executable, str(TOOL), "--dir", str(directory or self.assets),
             "--out", str(output or self.out), "--format", format, *extra],
            cwd=self.root, capture_output=True, text=True, timeout=15,
        )

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_failure(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_json_measures_nested_files_and_is_deterministic(self):
        entries = {
            "b/icon.png": png(7, 5),
            "a/icon.png": png(16, 8, colour=6, extra=srgb_chunk()),
            "rotated.jpg": jpeg_with(32, 16, [(0xE1, b"Exif\x00\x00" + exif(6))]),
            "shape.webp": webp_vp8l(9, 6, True),
            "tiny.gif": base64.b64decode(
                "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"),
        }
        for name, raw in entries.items():
            self.image(name, raw)
        (self.assets / "notes.txt").write_text("not an image", encoding="utf-8")
        out = self.out.with_suffix(".json")
        self.assert_success(self.run_catalog(output=out, format="json"))
        original = out.read_bytes()
        document = json.loads(original)
        self.assertEqual(document["schema_version"], 1)
        self.assertEqual(document["root"], "../assets")
        self.assertEqual([a["path"] for a in document["assets"]], sorted(entries))
        by_path = {a["path"]: a for a in document["assets"]}
        tagged = by_path["a/icon.png"]
        self.assertEqual((tagged["width"], tagged["height"], tagged["size"]),
                         (16, 8, "16x8"))
        self.assertTrue(tagged["alpha"])
        self.assertEqual(tagged["colour"], "sRGB tagged")
        rotated = by_path["rotated.jpg"]
        self.assertEqual((rotated["size"], rotated["displayed_size"],
                          rotated["orientation"]), ("32x16", "16x32", 6))
        self.assertEqual({a["format"] for a in document["assets"]},
                         {"PNG", "JPEG", "WebP", "GIF"})
        for name, raw in entries.items():
            self.assertEqual(by_path[name]["bytes"], len(raw))
            self.assertEqual((self.assets / name).read_bytes(), raw)
        self.assert_success(self.run_catalog(output=out, format="json", extra=["--replace"]))
        self.assertEqual(out.read_bytes(), original)

    def test_recipe_is_checked_and_linked_without_copying_its_prompt(self):
        generated = self.image("generated.png")
        sidecar = self.recipe(generated)
        photo = self.image("photo.png")
        before = {p: p.read_bytes() for p in (generated, sidecar, photo)}
        out = self.out.with_suffix(".json")
        self.assert_success(self.run_catalog(output=out, format="json"))
        document = json.loads(out.read_text(encoding="utf-8"))
        recipes = {a["path"]: a["recipe"] for a in document["assets"]}
        self.assertEqual(recipes["generated.png"], {
            "status": "checked", "path": "generated.png.recipe.yaml",
            "url": "../assets/generated.png.recipe.yaml",
        })
        self.assertEqual(recipes["photo.png"], {
            "status": "unknown", "path": None, "url": None,
        })
        self.assert_success(self.run_catalog())
        for output in (out, self.out):
            text = output.read_text(encoding="utf-8")
            self.assertNotIn("PRIVATE PROMPT", text)
            self.assertNotIn("/generator/source.png", text)
        links = Links(self.out.read_text(encoding="utf-8"))
        self.assertIn("../assets/generated.png.recipe.yaml",
                      [a.get("href") for a in links.anchors])
        for path, raw in before.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_html_escapes_names_and_urls_resolve_from_the_output(self):
        name = 'folder #&/日本語 "><img onerror=alert(1)>?.png'
        image = self.image(name)
        sidecar = self.recipe(image)
        self.assert_success(self.run_catalog())
        text = self.out.read_text(encoding="utf-8")
        links = Links(text)
        image_url = quote("../assets/" + name, safe="/")
        recipe_url = quote("../assets/" + name + ".recipe.yaml", safe="/")
        self.assertEqual(len(links.images), 1)
        self.assertEqual(links.images[0]["src"], image_url)
        self.assertNotIn("onerror", links.images[0])
        self.assertNotIn('<img onerror=alert(1)>', text)
        self.assertIn("&lt;img onerror=alert(1)&gt;", text)
        self.assertIn(image_url, [a.get("href") for a in links.anchors])
        self.assertIn(recipe_url, [a.get("href") for a in links.anchors])
        self.assertEqual((self.out.parent / unquote(image_url)).resolve(), image)
        self.assertEqual((self.out.parent / unquote(recipe_url)).resolve(), sidecar)

    def test_empty_directory_produces_an_empty_catalogue(self):
        out = self.out.with_suffix(".json")
        self.assert_success(self.run_catalog(output=out, format="json"))
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["assets"], [])
        self.assert_success(self.run_catalog())
        self.assertEqual(Links(self.out.read_text(encoding="utf-8")).images, [])

    def test_corrupt_or_incomplete_images_preserve_existing_catalogue(self):
        self.out.parent.mkdir()
        self.out.write_text("previous catalogue", encoding="utf-8")
        for data in (b"not an image", png(16, 8)[:-12]):
            with self.subTest(data=data[:12]):
                self.image("broken.png", data)
                result = self.run_catalog(extra=["--replace"])
                self.assert_failure(result)
                self.assertIn("broken.png", result.stderr)
                self.assertEqual(self.out.read_text(encoding="utf-8"), "previous catalogue")

    def test_invalid_recipe_blocks_catalogue_publication(self):
        image = self.image()
        sidecar = self.recipe(image)
        good = sidecar.read_text(encoding="utf-8")
        bad_size = yaml.safe_load(good)
        bad_size["size"]["on_disk"] = "999x999"
        for text in ("prompt: [broken", yaml.safe_dump(bad_size), "- not a mapping\n"):
            with self.subTest(recipe=text[:30]):
                sidecar.write_text(text, encoding="utf-8")
                result = self.run_catalog()
                self.assert_failure(result)
                self.assertIn(sidecar.name, result.stderr)
                self.assertFalse(self.out.exists())

    def test_sidecar_keeps_a_renamed_image_visible_to_validation(self):
        image = self.image("misnamed.data")
        self.recipe(image)
        result = self.run_catalog()
        self.assert_failure(result)
        self.assertIn("misnamed.data", result.stderr)
        self.assertFalse(self.out.exists())

    def test_replacement_is_explicit_and_does_not_modify_the_source(self):
        image = self.image()
        source = image.read_bytes()
        self.out.parent.mkdir()
        self.out.write_text("keep this", encoding="utf-8")
        self.assert_failure(self.run_catalog())
        self.assertEqual(self.out.read_text(encoding="utf-8"), "keep this")
        self.assert_success(self.run_catalog(extra=["--replace"]))
        self.assertEqual(len(Links(self.out.read_text(encoding="utf-8")).images), 1)
        self.assertEqual(image.read_bytes(), source)

    def test_output_cannot_replace_an_image_or_its_recipe(self):
        image = self.image()
        sidecar = self.recipe(image)
        for path in (image, sidecar):
            with self.subTest(output=path.name):
                original = path.read_bytes()
                self.assert_failure(self.run_catalog(output=path, extra=["--replace"]))
                self.assertEqual(path.read_bytes(), original)

    def test_output_links_are_refused_even_when_replacement_is_requested(self):
        self.image()
        victim = self.root / "other.html"
        victim.write_text("do not replace", encoding="utf-8")
        self.out.parent.mkdir()
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind):
                if kind == "symlink":
                    self.out.symlink_to(victim)
                else:
                    os.link(victim, self.out)
                self.assert_failure(self.run_catalog(extra=["--replace"]))
                self.assertEqual(victim.read_text(encoding="utf-8"), "do not replace")
                self.out.unlink()

    def test_external_image_and_recipe_symlinks_are_not_followed(self):
        outside = self.root / "outside.png"
        outside.write_bytes(png(16, 8))
        link = self.assets / "linked.png"
        link.symlink_to(outside)
        self.assert_failure(self.run_catalog())
        self.assertFalse(self.out.exists())
        link.unlink()
        image = self.image()
        sidecar = self.recipe(image)
        outside_recipe = self.root / "outside.recipe.yaml"
        sidecar.rename(outside_recipe)
        sidecar.symlink_to(outside_recipe)
        self.assert_failure(self.run_catalog())
        self.assertFalse(self.out.exists())

    def test_directory_symlinks_are_not_traversed(self):
        self.image()
        outside = self.root / "elsewhere"
        outside.mkdir()
        (outside / "private.png").write_bytes(png(3, 2))
        (self.assets / "outside").symlink_to(outside, target_is_directory=True)
        (self.assets / "loop").symlink_to(self.assets, target_is_directory=True)
        out = self.out.with_suffix(".json")
        self.assert_success(self.run_catalog(output=out, format="json"))
        self.assertEqual([a["path"] for a in json.loads(out.read_text())["assets"]],
                         ["hero.png"])

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires a POSIX FIFO")
    def test_special_image_file_is_refused_without_waiting_for_a_writer(self):
        os.mkfifo(self.assets / "pipe.png")
        self.assert_failure(self.run_catalog())
        self.assertFalse(self.out.exists())

    @unittest.skipUnless(os.name == "posix", "requires POSIX byte filenames")
    def test_non_utf8_filename_preserves_source_and_existing_catalogue(self):
        name = os.fsencode(self.assets) + b"/bad-\xff.png"
        original = png(16, 8)
        with open(name, "wb") as image:
            image.write(original)
        self.out.parent.mkdir()
        self.out.write_text("previous catalogue", encoding="utf-8")
        result = self.run_catalog(extra=["--replace"])
        self.assert_failure(result)
        self.assertTrue(result.stderr.strip())
        self.assertEqual(self.out.read_text(encoding="utf-8"), "previous catalogue")
        with open(name, "rb") as image:
            self.assertEqual(image.read(), original)

    def test_failed_atomic_replacement_preserves_previous_output(self):
        import catalog

        self.image()
        self.out.parent.mkdir()
        self.out.write_text("previous catalogue", encoding="utf-8")
        before = set(self.out.parent.iterdir())
        noise = io.StringIO()
        with mock.patch.object(catalog.os, "replace", side_effect=OSError("write failed")), \
                contextlib.redirect_stdout(noise), contextlib.redirect_stderr(noise):
            result = catalog.main(["--dir", str(self.assets), "--out", str(self.out),
                                   "--replace"])
        self.assertNotEqual(result, 0)
        self.assertEqual(self.out.read_text(encoding="utf-8"), "previous catalogue")
        self.assertEqual(set(self.out.parent.iterdir()), before)


if __name__ == "__main__":
    unittest.main()
