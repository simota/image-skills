<!-- image:deferred -->
Purpose: generate a browsable inventory of the images actually delivered.
Read when: placing images in a project, refreshing a delivered set, or asked for an asset catalog.
Source: none — this set owns the catalog format and the tool that writes it.
Verified: 2026-11-03 — `make catalog-test` checks measured fields, relative links,
escaping, recipe handling, and refusal paths; no automated check reads this prose.

# Asset catalog

Generate or refresh an HTML catalog after placement, following project access
policy. Default to `.agents/asset-catalog.html` and link it in the report.
Keep it with the asset tree: previews reference existing files; nothing is published.

Run the linked `catalog.py` from the project root. In these examples,
`IMAGE_DELIVER_DIR` is this skill's absolute directory:

```sh
python3 "$IMAGE_DELIVER_DIR/catalog.py" --dir assets --out .agents/asset-catalog.html
python3 "$IMAGE_DELIVER_DIR/catalog.py" --dir assets --out .agents/asset-catalog.json --format json
```

Emit JSON when another tool needs the inventory. Refresh with `--replace` after
verifying that the target is this delivery's catalog.

## What is measured

Recursively scan PNG, JPEG, WebP and GIF, including uppercase extensions and files
renamed since their sidecar was written. Record other delivered formats separately.

Entries carry relative paths and URLs, actual format, stored/displayed dimensions,
bytes, alpha and colour profile. Preview originals; keep duplicate basenames separate.
Sort by relative path without timestamps. Empty directories produce empty catalogs.

Header measurements cannot judge visual quality; open the final images.
Preview labels identify filenames, without deciding alt text for a later use.

Link existing sidecars and check them with `recipe.py`. Store their link and
status, never their prompts. A missing sidecar is `unknown`, not an error or
proof of generation. Preserve project provenance conventions, including manifests
and separate records; do not create sidecars solely for this catalog.

A malformed recipe, mismatched extension or incomplete image fails the run and
preserves the previous catalog. Resolve the diagnostics before trying again.

Read sources only. Skip directory symlinks; refuse image or recipe links outside
the asset root and non-regular inputs. Outputs use the selected format's extension
and cannot replace images or recipes. Refuse output symlinks and hard links even
with `--replace`. Write a temporary sibling and install it atomically, preserving
the previous catalog on failure.

Open the HTML, check its count, and follow image and recipe links. A non-zero exit
means no new catalog was delivered; report blocked files rather than calling an
old catalog current. Include the final files and use-specific accessibility decisions.
