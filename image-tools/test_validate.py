#!/usr/bin/env python3
"""Prove each rule in validate.py fires.

A check only ever seen passing may be checking nothing. Every rule below gets a
deliberate violation injected into a throwaway copy of the repo, and the test
fails if the validator stays quiet.

Run: make test
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True                     # no __pycache__ in the tools dir
import validate                                    # noqa: E402  — for RULES only


def run(root: Path) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(root / "image-tools" / "validate.py")],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


S = "skills/"          # everything the CLI reads lives here


def sub(path: Path, old: str, new: str) -> None:
    t = path.read_text(encoding="utf-8")
    assert old in t, f"fixture text not found in {path.name}: {old[:60]!r}"
    path.write_text(t.replace(old, new, 1), encoding="utf-8")


# Each case mutates a copy, then expects that rule id in the output — and, where
# `says` is given, a failure line of that rule containing it. The id alone
# cannot tell which branch fired, so a mutation that trips two branches proves
# neither: deleting either one still leaves the id in the output.
CASES: dict[str, callable] = {}
SAYS: dict[str, str] = {}


def case(rule, says: str | None = None):
    def deco(fn):
        CASES[rule] = fn
        if says:
            SAYS[rule] = says
        return fn
    return deco


@case("V1")
def _(r): sub(r / f"{S}image-prompt/SKILL.md", "## Owns", "## Owns\n" + "x\n" * 200)


@case("V2")
def _(r): sub(r / f"{S}image-prompt/SKILL.md", "Writing the generation prompt",
              "Not for image-generate. Writing the generation prompt")


@case("V3")
def _(r): (r / f"{S}image-ghost").mkdir(); (r / f"{S}image-ghost/SKILL.md").write_text("x")


@case("V4")
def _(r): (r / f"{S}image-prompt/playbooks/orphan.md").write_text("<!-- image:guidance -->\n")


@case("V5")
def _(r): (r / f"{S}image-prompt/playbooks/structure.md").write_text("y\n" * 400)


@case("V6")
def _(r): sub(r / f"{S}_image/VALUES.md", "## 1. Looking", "z\n" * 200 + "## 1. Looking")


@case("V7")
def _(r): sub(r / "image-registry/routes.yaml", "chain: [image-review, image-refine, image-review]",
              "chain: [image-review, image-nonexistent, image-review]")


@case("V8")
def _(r): sub(r / "README.md", "](skills/_image/ROUTING.md)", "](skills/_image/GONE.md)")


@case("V9")
def _(r): sub(r / "image-registry/capabilities.yaml", "signals: [generation prompt, prompt wording",
              "signals: [artefacts, prompt wording")


@case("V10")
def _(r): sub(r / "image-registry/fixtures.yaml",
              '- ask: "is this usable or not"\n  expect: image-review',
              '- ask: "is this usable or not"\n  expect: image-deliver')


@case("V11")
def _(r):
    import shutil
    for i in range(4):
        d = r / f"{S}image-extra{i}"
        d.mkdir()
        shutil.copy(r / f"{S}image-prompt/SKILL.md", d / "SKILL.md")


@case("V12")
def _(r): (r / f"{S}rogue").mkdir(); (r / f"{S}rogue/SKILL.md").write_text("x")


@case("V13")
def _(r):
    t = (r / "image-registry/routes.yaml").read_text(encoding="utf-8")
    t += "".join(f"\nfiller{i}:\n  pattern: linear\n  when: x\n  chain: [image-prompt]\n"
                 for i in range(20))
    (r / "image-registry/routes.yaml").write_text(t, encoding="utf-8")


@case("V14")
def _(r): sub(r / "image-registry/routes.yaml", "  pattern: loop", "  pattern: spiral")


@case("V15")
def _(r): sub(r / f"{S}image-review/SKILL.md", "allowed-tools: Read, Grep, Glob, Bash",
              "allowed-tools: Read, Grep, Glob, Edit, Write, Bash")


@case("V16")
def _(r): sub(r / f"{S}image-prompt/SKILL.md", "## Done when", "## Finished when")


@case("V17")
def _(r): sub(r / f"{S}image-prompt/SKILL.md", "- **Grade every claim**", "- **Grade some claims**")


@case("V18")
def _(r): sub(r / f"{S}image-prompt/SKILL.md", "prompt wording", "prompt phrasing")


@case("V19")
def _(r): sub(r / f"{S}image-prompt/SKILL.md", "`_image/SIZING.md`", "`../_image/SIZING.md`")


@case("V19-shared")
def _(r): sub(r / f"{S}_image/ROUTING.md", "(`_image/SIZING.md`)", "(`SIZING.md`)")


@case("V20")
def _(r):
    """The definition row becomes a mention; the word is still on the page."""
    sub(r / f"{S}_image/CONTRACT.md", "| `asserted` |", "| asserted |")


@case("V21")
def _(r):
    f = r / f"{S}image-prompt/SKILL.md"
    body = f.read_text(encoding="utf-8")
    head, rest = body.split("## Verify with\n", 1)
    keep, tail = rest.split("<!-- deliver:report -->", 1)
    for grade in ("measured", "inspected", "asserted"):
        keep = keep.replace(grade, "checked")   # backticked and bare alike
    f.write_text(head + "## Verify with\n" + keep + "<!-- deliver:report -->" + tail,
                 encoding="utf-8")


@case("V22")
def _(r): sub(r / f"{S}image-prompt/SKILL.md", "## Done when",
              "## Done when\n\n#" + "TODO(agent): tidy this up later\n")


@case("V23")
def _(r): sub(r / f"{S}_image/VALUES.md", "<!-- image:contract -->", "<!-- image:guidance -->")


@case("V24")
def _(r): sub(r / f"{S}_image/ROUTING.md", "`image-refine`", "`image-fix`")


@case("V25")
def _(r): sub(r / f"{S}image-prompt/playbooks/structure.md", "# ", "# pinned at v2.14.0 — ")


@case("V26")
def _(r): sub(r / "image-registry/capabilities.yaml", "      go: image-refine",
              "      go: image-fix")


@case("V27")
def _(r):
    (r / f"{S}image-prompt/_image").unlink()
    (r / f"{S}image-prompt/_image").symlink_to("../_gone")


@case("V28")
def _(r): sub(r / "image-registry/harness.yaml", "set: image", "set: ui")


@case("V28-generic-dir")
def _(r): (r / "registry").mkdir()


@case("V29")
def _(r):
    f = r / f"{S}image-prompt/reference/sizes.md"
    f.write_text(f.read_text(encoding="utf-8").replace("Verified:", "Checked:"), encoding="utf-8")


@case("V30")
def _(r): (r / f"{S}image-prompt/reference/orphan.md").write_text(
    "<!-- image:deferred -->\n# Orphan\n\nPurpose: x\nRead when: y\n"
    "Verified: 2026-08-23 — no automated check\n")


@case("V31")
def _(r):
    for f in sorted((r / f"{S}").glob("*/reference/*.md")):
        t = f.read_text()
        i = t.index("Verified:")
        j = t.index("\n\n", i)
        f.write_text(t[:i] + "Verified: 2026-08-21" + t[j:])
        return


@case("V32")
def _(r):
    sub(r / "image-registry/routes.yaml", "checker: ", "checker: claude  # ")


@case("V32-unknown")
def _(r):
    sub(r / "image-registry/routes.yaml", "checker: ", "checker: nosuchengine  # ")



@case("V32-single")
def _(r):
    sub(r / "image-registry/harness.yaml",
        "runs_on: [claude, codex, agy]", "runs_on: [claude]")



@case("V33")
def _(r):
    sub(r / "image-registry/harness.yaml", "  lens: |", "  lens: ''\n  unused: |")



@case("V34", says="cannot reach")
def _(r):
    """Runnable and declared, and out of reach."""
    (r / "skills/image-review/refute.py").unlink()


@case("V34-decoration", says="grants no Bash")
def _(r):
    """A link where the class grants no shell reads like a capability and is not
    one. Every class this set declares grants Bash, so the case adds one that
    does not; picking an existing class without Bash found none and fell
    through to a different branch."""
    sub(r / "image-registry/harness.yaml", "permission_classes:\n",
        "permission_classes:\n  no-shell:\n    tools: \"Read, Grep, Glob\"\n"
        "    writes: false\n")
    sub(r / "image-registry/capabilities.yaml",
        "image-review:\n  class: read-only", "image-review:\n  class: no-shell")


@case("V34-wrong-target", says="not the set's own")
def _(r):
    link = r / "skills/image-review/refute.py"
    link.unlink()
    link.symlink_to("../../image-tools/render.py")   # the set's own, but the wrong tool


@case("V34-undeclared")
def _(r):
    """A tool link nothing declares is a capability nobody decided to grant."""
    (r / "skills/image-review/render.py").symlink_to("../../image-tools/render.py")


@case("V34-wrong-skill")
def _(r):
    """Declared for some skills, linked into one it is not declared for."""
    (r / "skills/image-review/recipe.py").symlink_to("../../image-tools/recipe.py")


@case("V34-missing-tool")
def _(r): sub(r / "image-registry/harness.yaml",
              "  refute.py: all", "  refute.py: all\n  nosuch.py: all")


@case("V34-none-declared")
def _(r): sub(r / "image-registry/harness.yaml", "linked_tools:", "unlinked_tools:")


@case("V35")
def _(r): sub(r / f"{S}image-prompt/SKILL.md",
              "states `IRREPRODUCIBLE` when", "states exact regeneration is unavailable when")


@case("V36")
def _(r): (r / f"{S}image-review/playbooks/visualise.md").unlink()


@case("V36-undefined")
def _(r):
    """A trigger the registry declares and the pages never define."""
    f = r / f"{S}image-review/playbooks/visualise.md"
    ref = r / f"{S}image-review/reference/diagram-forms.md"
    for g in (f, ref):
        g.write_text(g.read_text(encoding="utf-8").replace("`ordering`", "sequencing"),
                     encoding="utf-8")


@case("V36-unreachable")
def _(r): sub(r / f"{S}image-review/SKILL.md",
              "[visualise](playbooks/visualise.md)", "the visualise guidance")


@case("V36-none-declared")
def _(r): sub(r / "image-registry/harness.yaml", "finding_visuals:", "unused_visuals:")


@case("V38")
def _(r): sub(r / f"{S}image-prompt/playbooks/exclusions.md", "<!-- image:guidance -->\n",
              "<!-- image:guidance -->\nverdict: KEEP | DROP\n")


@case("V37")
def _(r):
    """A page that leans on a declared source and does not say so."""
    sub(r / f"{S}image-generate/reference/codex-imagen.md",
        "Source: codex — the flags and defaults below are that CLI's, and move with its releases.",
        "Source: none — nothing outside this page can move what it states.")


@case("V37-unused")
def _(r):
    """A source named in the header that the page never uses."""
    sub(r / f"{S}image-review/reference/report-template.md",
        "Source: none — nothing outside this page can move what it states.",
        "Source: codex — the flags and defaults below are that CLI's, and move with its releases.")


@case("V37-silent")
def _(r):
    """Neither a source nor the admission that there is none."""
    sub(r / f"{S}image-review/reference/report-template.md",
        "Source: none — nothing outside this page can move what it states.", "Source:")


@case("V37-none-declared")
def _(r): sub(r / "image-registry/harness.yaml", "source_authorities:", "unused_authorities:")


@case("V39")
def _(r):
    sub(r / "image-registry/routes.yaml",
        "chain: [image-review, image-refine, image-review]",
        "chain: [image-review, image-refine]")


@case("V39-set")
def _(r):
    import yaml
    f = r / "image-registry/routes.yaml"
    routes = yaml.safe_load(f.read_text())
    routes["asset-set"]["chain"].remove("image-review")
    f.write_text(yaml.safe_dump(routes, sort_keys=False))


@case("V39-ship")
def _(r):
    sub(r / "image-registry/routes.yaml",
        "chain: [image-prompt, image-generate, image-review, image-deliver]",
        "chain: [image-prompt, image-generate, image-deliver]")


@case("V39-restyle")
def _(r):
    sub(r / "image-registry/routes.yaml",
        "chain: [image-direction, image-refine, image-review]",
        "chain: [image-direction, image-refine]")


@case("V39-before-change")
def _(r):
    sub(r / "image-registry/routes.yaml",
        "chain: [image-prompt, image-generate, image-review, image-deliver]",
        "chain: [image-prompt, image-review, image-generate, image-deliver]")


@case("V39-after-delivery")
def _(r):
    sub(r / "image-registry/routes.yaml",
        "chain: [image-prompt, image-generate, image-review, image-deliver]",
        "chain: [image-prompt, image-generate, image-deliver, image-review]")


@case("V39-vacuous")
def _(r):
    sub(r / "image-registry/capabilities.yaml",
        "off-brief-drift, severity-ranking, verdict]",
        "off-brief-drift, severity-ranking]")


@case("V10-empty", says="vacuous")
def _(r): (r / "image-registry/fixtures.yaml").write_text("{}\n", encoding="utf-8")


@case("V13-stages", says="stages")
def _(r):
    sub(r / "image-registry/routes.yaml",
        "chain: [image-direction, image-prompt, image-generate, image-review, image-deliver]",
        "chain: [image-direction, image-prompt, image-generate, image-review, "
        "image-refine, image-review, image-deliver]")


@case("V19-reference", says="does not resolve")
def _(r):
    f = r / f"{S}image-prompt/reference/sizes.md"
    f.write_text(f.read_text(encoding="utf-8") + "\nSee `_image/NOPE.md`.\n",
                 encoding="utf-8")


@case("V22-code-on-line", says="residual class")
def _(r):
    f = r / f"{S}image-prompt/playbooks/structure.md"
    f.write_text(f.read_text(encoding="utf-8")
                 + "\n#" + "TODO(agent): tidy `this` up later\n", encoding="utf-8")


@case("V26-bare", says="not a skill")
def _(r):
    t = (r / "image-registry/capabilities.yaml").read_text(encoding="utf-8")
    import re as _re
    m = _re.search(r"go: (image-[a-z]+)", t)
    (r / "image-registry/capabilities.yaml").write_text(
        t.replace(m.group(0), "go: refine", 1), encoding="utf-8")


@case("V27-nested", says="outside the repo")
def _(r):
    (r / f"{S}image-prompt/playbooks/leak.md").symlink_to("/etc/hostname")


@case("V38-comment", says="MAYBE")
def _(r):
    sub(r / f"{S}_image/HANDOFF.md", "DONE | PARTIAL | BLOCKED", "DONE | PARTIAL | BLOCKED | MAYBE")


@case("V39-verb", says="no skill does")
def _(r):
    sub(r / "image-registry/harness.yaml", "reviews: [verdict]", "reviews: [verdict, judgement]")


@case("V1-folded", says="description is")
def _(r):
    # A folded scalar is how a long description gets written, and a line
    # parser reads it as the two characters `>-` — always under the limit.
    f = r / f"{S}image-prompt/SKILL.md"
    t = f.read_text(encoding="utf-8")
    start = t.index("description:")
    end = t.index("\n", start)
    f.write_text(t[:start] + "description: >-\n  " + "word " * 60 + t[end:],
                 encoding="utf-8")


@case("V1-yaml", says="frontmatter")
def _(r):
    sub(r / f"{S}image-prompt/SKILL.md", "name: image-prompt", "name: [image-prompt")


@case("V24-hyphen", says="image-colour-grade")
def _(r):
    f = r / f"{S}_image/ROUTING.md"
    f.write_text(f.read_text(encoding="utf-8") + "\nSee `image-colour-grade`.\n",
                 encoding="utf-8")


@case("V10-substring", says="no signal matches")
def _(r):
    # A signal inside a longer word is not that signal — `seed` is not in
    # `seedling` — so a fixture that only matches that way matches nothing.
    import yaml as _y
    caps = _y.safe_load((r / "image-registry/capabilities.yaml").read_text())
    sig = next(s for s in caps["image-refine"]["signals"] if " " not in s)
    f = r / "image-registry/fixtures.yaml"
    f.write_text(f.read_text(encoding="utf-8")
                 + f"\n- ask: \"x{sig}y\"\n  expect: image-refine\n",
                 encoding="utf-8")


@case("V17-missing-source", says="no delivered/")
def _(r):
    sub(r / "image-registry/harness.yaml", "delivered:\n", "delivered:\n  nosuch:\n"
        "    section: Owns\n")


@case("V22-between-spans", says="residual class")
def _(r):
    # The text between two code spans is not code, whichever backtick a
    # pattern happens to start from.
    f = r / f"{S}image-prompt/playbooks/structure.md"
    f.write_text(f.read_text(encoding="utf-8") + "\nRun `make check` #"
                 "TODO(agent): fix the walker `later`\n", encoding="utf-8")


@case("V19-nested", says="does not resolve")
def _(r):
    sub_dir = r / f"{S}image-prompt/reference/deeper"
    sub_dir.mkdir()
    (sub_dir / "x.md").write_text("<!-- image:deferred -->\nSee `playbooks/nope.md`.\n",
                                  encoding="utf-8")


@case("V19-harness-path", says="image-tools/nope.py")
def _(r):
    f = r / f"{S}image-prompt/reference/sizes.md"
    f.write_text(f.read_text(encoding="utf-8") + "\nSee `image-tools/nope.py`.\n",
                 encoding="utf-8")


@case("V2-capitalised", says="'rather than'")
def _(r): sub(r / f"{S}image-deliver/SKILL.md", "Use once the image is chosen.",
              "Rather than polishing, use once the image is chosen.")


@case("V7-misspelt-chain", says="has no chain")
def _(r):
    f = r / "image-registry/routes.yaml"
    f.write_text(f.read_text(encoding="utf-8") + "\nshortcut:\n  pattern: linear\n"
                 "  when: x\n  chian: [image-generate, image-deliver]\n", encoding="utf-8")


@case("V7-empty-chain", says="has no chain")
def _(r):
    f = r / "image-registry/routes.yaml"
    f.write_text(f.read_text(encoding="utf-8") + "\nshortcut:\n  pattern: linear\n"
                 "  when: x\n  chain:\n", encoding="utf-8")


@case("V16-fenced-heading", says="missing section 'Done when'")
def _(r): sub(r / f"{S}image-refine/SKILL.md", "\n## Done when\n",
              "\n```text\n## Done when\n```\n")


@case("V17-blank-line", says="differs")
def _(r): sub(r / f"{S}image-review/SKILL.md", "<!-- deliver:sizing -->\n",
              "<!-- deliver:sizing -->\n\n")


@case("V17-duplicated", says="duplicated")
def _(r):
    f = r / f"{S}image-refine/SKILL.md"
    t = f.read_text(encoding="utf-8")
    block = t[t.index("<!-- deliver:values -->"):t.index("<!-- /deliver:values -->")]
    f.write_text(t + "\n" + block + "<!-- /deliver:values -->\n", encoding="utf-8")


@case("V19-shared-per-skill", says="as read by image-review")
def _(r): sub(r / f"{S}_image/CONTRACT.md", "(`imgfacts.py`)", "(`strip.py`)")


@case("V29-nested", says="has no 'Purpose:'")
def _(r):
    sub_dir = r / f"{S}image-deliver/reference/formats"
    sub_dir.mkdir()
    (sub_dir / "avif.md").write_text("<!-- image:deferred -->\nAVIF.\n", encoding="utf-8")


@case("V34-whole-directory", says="reaches image-tools/")
def _(r): (r / f"{S}image-generate/tools").symlink_to("../../image-tools")


@case("V34-ancestor", says="reaches image-tools/")
def _(r): (r / f"{S}image-review/playbooks/root").symlink_to("../../..")


@case("V30-skill-relative-link", says="orphan.md is reachable from nothing")
def _(r):
    # A Markdown link resolves from its own page; read from the skill root it
    # made a page the link does not reach look linked.
    (r / f"{S}image-prompt/reference/orphan.md").write_text(
        "<!-- image:deferred -->\n", encoding="utf-8")
    f = r / f"{S}image-prompt/playbooks/structure.md"
    f.write_text(f.read_text(encoding="utf-8") + "\nSee [o](reference/orphan.md).\n",
                 encoding="utf-8")


@case("V4-commented-out", says="severity.md is not linked")
def _(r):
    # A row commented out is not shown, so nothing a reader sees leads there.
    row = "| Deciding how much a defect matters | [severity](playbooks/severity.md)"
    sub(r / f"{S}image-review/SKILL.md", row, "<!--\n" + row)
    sub(r / f"{S}image-review/SKILL.md", "not by how odd it is up close |",
        "not by how odd it is up close |\n-->")


@case("V30-code-span", says="defect-catalogue.md is reachable from nothing")
def _(r): sub(r / f"{S}image-review/SKILL.md",
              "[defect-catalogue](reference/defect-catalogue.md)",
              "`[defect-catalogue](reference/defect-catalogue.md)`")


@case("V4-nested-copy", says="playbooks/old/structure.md")
def _(r):
    (r / f"{S}image-prompt/playbooks/old").mkdir()
    shutil.copy(r / f"{S}image-prompt/playbooks/structure.md",
                r / f"{S}image-prompt/playbooks/old/structure.md")


# --- round six: rules that were vacuous on ordinary ways of writing ----------

@case("V8-image-syntax", says="links to missing")
def _(r):
    """Prose outside code still counts once code is set aside."""
    sub(r / f"{S}image-deliver/playbooks/naming.md", "\n## ",
        "\nSee `![alt](hero.png)` and [the old page](gone.md).\n\n## ")


@case("V10-shape", says="needs an `ask` and an `expect`")
def _(r): sub(r / "image-registry/fixtures.yaml", "- ask: \"we need a hero picture",
              "- asks: \"we need a hero picture")


@case("V11-packs", says="packs_needed_above")
def _(r): sub(r / "image-registry/harness.yaml", "packs_needed_above: 20",
              "packs_needed_above: 3")


@case("V15-writes", says="writes: False")
def _(r): sub(r / "image-registry/harness.yaml", "tools: \"Read, Grep, Glob, Bash\"\n    writes: false",
              "tools: \"Read, Grep, Glob, Bash, Edit\"\n    writes: false")


@case("V19-link", says="links to '../_image/CONTRACT.md'")
def _(r): sub(r / f"{S}image-review/SKILL.md", "## Owns",
              "## Owns\n\nSee [CONTRACT](../_image/CONTRACT.md).\n")


@case("V19-link-tools", says="links to '../../image-tools/imgfacts.py'")
def _(r): sub(r / f"{S}image-review/SKILL.md", "## Owns",
              "## Owns\n\nRun [imgfacts](../../image-tools/imgfacts.py).\n")


@case("V23-vocabulary", says="not one of document_labels")
def _(r): sub(r / "image-registry/harness.yaml", '"skills/*/playbooks/*.md": guidance',
              '"skills/*/playbooks/*.md": guidence')


def _drop_line(path: Path, start: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [l for l in lines if not l.startswith(start)]
    assert len(kept) == len(lines) - 1, f"no single line opens with {start!r}"
    path.write_text("".join(kept), encoding="utf-8")


@case("V24-routing-row", says="has no table row for image-deliver")
def _(r): _drop_line(r / f"{S}_image/ROUTING.md", "| `image-deliver` |")


@case("V24-readme-row", says="README.md has no table row for image-prompt")
def _(r): _drop_line(r / "README.md", "| [`image-prompt`]")


@case("V8-list-items", says="links to missing gone.md")
def _(r):
    """A lone backtick in one list item does not pair with one in the next."""
    sub(r / f"{S}image-deliver/playbooks/naming.md", "\n## ",
        "\n- Press the ` key to toggle.\n- See [guide](gone.md) and use `x` here.\n\n## ")


@case("V25-case")
def _(r): sub(r / f"{S}image-prompt/playbooks/structure.md", "# ", "# Imagen 4 reads text worse — ")


@case("V25-gpt")
def _(r): sub(r / f"{S}image-prompt/playbooks/structure.md", "# ", "# on gpt-5 — ")


@case("V25-month")
def _(r): sub(r / f"{S}image-prompt/playbooks/structure.md", "# ", "# checked in August 2026 — ")


@case("V25-slash")
def _(r): sub(r / f"{S}image-prompt/playbooks/structure.md", "# ", "# held in 2026/08 — ")


@case("V26-shape", says="is not a mapping")
def _(r): sub(r / "image-registry/capabilities.yaml",
              "    - what: \"wording the request the model actually receives\"\n      go: image-prompt",
              "    - image-prompt")


@case("V34-copy", says="holds a copy of strip.py")
def _(r): shutil.copy(r / "image-tools/strip.py", r / "skills/image-review/strip.py")


# The other half: edits a rule must stay quiet about. A rule that fires on
# ordinary writing gets switched off, which is a slower way to have no rule.
QUIET: dict[str, callable] = {}


def quiet(name):
    def deco(fn):
        QUIET[name] = fn
        return fn
    return deco


@quiet("a heading that names formats is not an enumeration")
def _(r):
    f = r / f"{S}image-deliver/reference/export-targets.md"
    f.write_text(f.read_text(encoding="utf-8") + "\n# PNG | WEBP\n\n# Output: PNG | WEBP\n"
                 "\n  # Output: PNG | WEBP\n", encoding="utf-8")   # indented, still a heading


@quiet("a heading quoted in a fence opens no section")
def _(r): sub(r / f"{S}image-refine/SKILL.md", "## Verify with\n",
              "## Verify with\n\n```markdown\n## Edit log\n```\n")


@quiet("a marker in double-backtick code is quoted too")
def _(r):
    f = r / f"{S}image-prompt/playbooks/structure.md"
    f.write_text(f.read_text(encoding="utf-8")
                 + "\nWrite ``#" + "TODO(agent): <action>`` with a class.\n",
                 encoding="utf-8")


@case("V38-fenced-comment", says="MAYBE")
def _(r):
    # Inside a fence a leading `#` is a comment in the schema, not a heading.
    f = r / f"{S}image-review/reference/report-template.md"
    f.write_text(f.read_text(encoding="utf-8")
                 + "\n```yaml\n# status: DONE | MAYBE\n```\n", encoding="utf-8")


@case("V38-nested-fence", says="MAYBE")
def _(r):
    # Inside a four-backtick fence a three-backtick line is content, not a
    # fence; toggling on it called the rest of the block unfenced.
    f = r / f"{S}image-review/reference/report-template.md"
    f.write_text(f.read_text(encoding="utf-8")
                 + "\n````md\n```\n# status: DONE | MAYBE\n```\n````\n",
                 encoding="utf-8")


@quiet("a backtick run with a backtick in its info string opens no fence")
def _(r):
    # CommonMark: such a line is a paragraph, so the heading after it is still
    # a heading — and a heading names things, it switches on nothing.
    f = r / f"{S}image-review/reference/report-template.md"
    f.write_text(f.read_text(encoding="utf-8")
                 + "\n```bad`info\n\n# status: DONE | MAYBE\n", encoding="utf-8")


@quiet("a marker inside a code span that runs across lines is quoted")
def _(r):
    f = r / f"{S}image-prompt/playbooks/structure.md"
    f.write_text(f.read_text(encoding="utf-8")
                 + "\nA span can run on: `first line\n#" + "TODO(agent): <action>\nand close` here.\n",
                 encoding="utf-8")


@case("V22-after-multiline-span", says="residual class")
def _(r):
    # The span closes, and a live marker after it on the same paragraph is live.
    f = r / f"{S}image-prompt/playbooks/structure.md"
    f.write_text(f.read_text(encoding="utf-8")
                 + "\nA span `runs\non` and then #" + "TODO(agent): fix this\n",
                 encoding="utf-8")


@case("V22-across-blocks", says="residual class")
def _(r):
    # A heading is a block of its own: a backtick it leaves open cannot pair
    # with one in the paragraph below and hide the marker between them.
    f = r / f"{S}image-prompt/playbooks/structure.md"
    f.write_text(f.read_text(encoding="utf-8")
                 + "\n## A heading with a stray `\n#" + "TODO(agent): fix\nand a line with `\n",
                 encoding="utf-8")


@quiet("a code span inside a block quote runs across its quoted lines")
def _(r):
    f = r / f"{S}image-prompt/playbooks/structure.md"
    f.write_text(f.read_text(encoding="utf-8")
                 + "\n> A span `starts\n> #" + "TODO(agent): example\n> closes` here\n",
                 encoding="utf-8")


@case("V22-quoted-blank", says="residual class")
def _(r):
    # A `>` with nothing after it is a blank line inside the quote: the
    # paragraphs either side cannot pair backticks across it.
    f = r / f"{S}image-prompt/playbooks/structure.md"
    f.write_text(f.read_text(encoding="utf-8")
                 + "\n> one `\n>\n> #" + "TODO(agent): fix `\n", encoding="utf-8")


@quiet("a quoted marker is talked about, not left behind")
def _(r):
    f = r / f"{S}image-prompt/playbooks/structure.md"
    f.write_text(f.read_text(encoding="utf-8")
                 + "\nA marker reads `#" + "TODO(agent): <action>` in a document.\n",
                 encoding="utf-8")


@quiet("an image link quoted as code, a link title and angle brackets are not missing files")
def _(r):
    sub(r / f"{S}image-prompt/playbooks/structure.md", "\n## ",
        "\nWrite alt text as `![alt](hero.png)`; see [this](exclusions.md \"Exclusions\") "
        "and [that](<exclusions.md>).\n\n```md\n[an example](not-here.md)\n```\n\n## ")


@quiet("pixel arithmetic and words that open like a month are not dates")
def _(r):
    sub(r / f"{S}image-generate/playbooks/batching.md", "\n## ",
        "\nDecrease 2048 to 1024 for a thumbnail; a 2048/16 grid gives 128 px cells. "
        "Mark 1920 wide, and a marker 2000 px.\n\n## ")


@quiet("a link in an indented code block is an example")
def _(r):
    sub(r / f"{S}image-generate/playbooks/batching.md", "\n## ",
        "\nFor example:\n\n    [label](missing.md)\n\n## ")


@case("V8-quoted-fence", says="links to missing gone.md")
def _(r):
    """A fence left open inside a quote closes with the quote."""
    sub(r / f"{S}image-deliver/playbooks/naming.md", "\n## ",
        "\n> ```\n> example\n\nSee [guide](gone.md).\n\n## ")


@case("V8-nested-quoted-fence", says="links to missing gone.md")
def _(r):
    """A fence left open two quotes deep closes when the inner quote does."""
    sub(r / f"{S}image-deliver/playbooks/naming.md", "\n## ",
        "\n> > ```\n> > example\n> See [guide](gone.md).\n\n## ")


@case("V8-quote-depth", says="links to missing gone.md")
def _(r):
    """A backtick one quote deep does not pair with one two quotes deep."""
    sub(r / f"{S}image-deliver/playbooks/naming.md", "\n## ",
        "\n> Press ` to toggle.\n> > See [guide](gone.md) and `x`.\n\n## ")


@case("V8-thematic-break", says="links to missing gone.md")
def _(r):
    """A thematic break ends a quoted paragraph; it is no lazy continuation."""
    sub(r / f"{S}image-deliver/playbooks/naming.md", "\n## ",
        "\n> Press ` to toggle.\n***\nSee [guide](gone.md) and `x`.\n\n## ")


@case("V8-html-block", says="links to missing gone.md")
def _(r):
    """An HTML comment interrupts a quoted paragraph; it is no lazy continuation."""
    sub(r / f"{S}image-deliver/playbooks/naming.md", "\n## ",
        "\n> Press ` to toggle.\n<!-- end quote -->\nSee [guide](gone.md) and `x`.\n\n## ")


@quiet("a lazy continuation keeps a quoted code span whole")
def _(r):
    sub(r / f"{S}image-generate/playbooks/batching.md", "\n## ",
        "\n> Quote `[x](not-a-link.md)\nstill code` here.\n\n## ")


@quiet("an indented or fenced example inside a block quote is code too")
def _(r):
    sub(r / f"{S}image-generate/playbooks/batching.md", "\n## ",
        "\n> For example:\n>\n>     [label](missing.md)\n\n"
        "> ```md\n> [other](missing-too.md)\n> ```\n\n## ")


@quiet("a code span runs across the lines of one block quote")
def _(r):
    sub(r / f"{S}image-generate/playbooks/batching.md", "\n## ",
        "\n> Quote `[x](not-a-link.md)\n> still code` here.\n\n## ")


@quiet("a repeated heading is the one render.py writes under: the first")
def _(r):
    f = r / f"{S}image-review/SKILL.md"
    f.write_text(f.read_text(encoding="utf-8") + "\n## Before starting\n",
                 encoding="utf-8")


@quiet("a one-line comment ends where it closes, and the link after it counts")
def _(r): sub(r / f"{S}image-review/SKILL.md",
              "| Deciding how much a defect matters |",
              "<!-- a note -->\n| Deciding how much a defect matters |")


@quiet("a link that climbs within the skill resolves")
def _(r):
    sub(r / f"{S}image-review/playbooks/seeing.md", "\n## ",
        "\nThe forms are in [diagram forms](../reference/diagram-forms.md).\n\n## ")


# --- round seven: rules that passed what they exist to catch ------------------

@case("V14-oracle-blank", says="oracle")
def _(r): sub(r / "image-registry/routes.yaml",
              'oracle: "no open defect at severity major or above, and one full pass '
              'over the image adds none"', 'oracle: ""')


@case("V14-cycles-prose", says="max_cycles")
def _(r): sub(r / "image-registry/routes.yaml", "max_cycles: 4 ",
              "max_cycles: until it looks right ")


@case("V17-undeclared", says="not declared")
def _(r):
    """A key retired from `delivered:` leaves its blocks frozen in every
    SKILL.md, unrendered and unchecked, and their words read as the skill's own."""
    sub(r / "image-registry/harness.yaml", '  surface: { section: "Done when" }\n', "")


@case("V20-shared-word", says="'BLOCKED'")
def _(r):
    """BLOCKED is a status and a residual class; one row cannot define both."""
    sub(r / f"{S}_image/CONTRACT.md",
        "| `BLOCKED` | Could not proceed. Say what was tried and what stopped it |\n", "")


@case("V20-mention", says="'T1'")
def _(r):
    """A word in a later cell of some row is a mention, not a definition."""
    sub(r / f"{S}_image/SIZING.md",
        "| `T1` | One skill owns it, but a `T0` condition fails |",
        "| one skill owns it | `T1` | (moved) |")


@case("V8-reference-link", says="gone-away.md")
def _(r): sub(r / f"{S}image-generate/playbooks/batching.md", "\n## ",
              "\nSee [the old page][old].\n\n[old]: gone-away.md\n\n## ")


@case("V8-empty-alt", says="gone-away.png")
def _(r): sub(r / f"{S}image-generate/playbooks/batching.md", "\n## ",
              "\n![](gone-away.png)\n\n## ")


@case("V37-capitalised", says="leans on codex")
def _(r):
    """A sentence that opens with the tool's name still leans on it."""
    f = r / f"{S}image-deliver/reference/alt-text.md"
    f.write_text(f.read_text(encoding="utf-8") + "\nThe defaults follow Codex's imagegen skill.\n",
                 encoding="utf-8")


@case("V38-trailing-stop", says="CRITICAL")
def _(r): sub(r / f"{S}image-generate/playbooks/batching.md", "\n## ",
              "\nSeverity: CRITICAL | HIGH | LOW.\n\n## ")


@case("V7-not-a-mapping", says="not a mapping")
def _(r):
    f = r / "image-registry/routes.yaml"
    f.write_text(f.read_text(encoding="utf-8") + "\nquick: [image-prompt, image-generate]\n",
                 encoding="utf-8")


@case("V3-empty-stub", says="image-extra")
def _(r):
    """The first step of adding a skill; a traceback reported nothing at all."""
    f = r / "image-registry/capabilities.yaml"
    f.write_text(f.read_text(encoding="utf-8") + "\nimage-extra:\n", encoding="utf-8")


@quiet("pixel arithmetic over a 20xx width is not a date")
def _(r): sub(r / f"{S}image-generate/playbooks/batching.md", "\n## ",
              "\nOn a 12-column layout, 1920/12 gives 160 px columns, "
              "and 2048/10 is about 205.\n\n## ")


@quiet("a bracketed reference destination may hold a space")
def _(r):
    (r / f"{S}image-generate/playbooks/my notes.png").write_bytes(b"")
    sub(r / f"{S}image-generate/playbooks/batching.md", "\n## ",
        "\nSee [the notes][n].\n\n[n]: <my notes.png>\n\n## ")


def main() -> int:
    code, baseline = run(ROOT)
    if code != 0:
        print("the working tree is already failing; fix that first:\n" + baseline)
        return 1

    bad: list[str] = []
    for rule, mutate in CASES.items():
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "repo"
            shutil.copytree(ROOT, copy, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            mutate(copy)
            _, out = run(copy)
            expect = rule.split("-")[0]
            says = re.escape(SAYS.get(rule, ""))
            if not re.search(rf"^\s*{expect}: .*{says}", out, re.M):
                bad.append(rule)
                print(f"  {rule} did not fire\n{out}")

    for name, mutate in QUIET.items():
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "repo"
            shutil.copytree(ROOT, copy, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            mutate(copy)
            code, out = run(copy)
            if code != 0:
                bad.append(f"quiet: {name}")
                print(f"  a rule fired on: {name}\n{out}")

    print(f"{len(CASES)} rules exercised, {len(QUIET)} quiet cases, "
          f"{len(bad)} wrong")
    if bad:
        print("wrong: " + ", ".join(bad))
        return 1

    # Counting the cases that exist says nothing about the rules that do. A rule
    # added without a case left this printing "every rule fires" about it.
    covered = {c.split("-")[0] for c in CASES}
    declared = {fn.__name__.split("_")[0].upper() for fn in validate.RULES}
    untested = sorted(declared - covered, key=lambda r: int(r[1:]))
    if untested:
        print("no deliberate violation is injected for: " + ", ".join(untested))
        return 1
    print(f"every rule fires ({len(declared)} rules, {len(CASES)} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
