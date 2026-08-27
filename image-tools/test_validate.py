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


def run(root: Path) -> str:
    r = subprocess.run([sys.executable, str(root / "image-tools" / "validate.py")],
                       capture_output=True, text=True)
    return r.stdout + r.stderr


S = "skills/"          # everything the CLI reads lives here


def sub(path: Path, old: str, new: str) -> None:
    t = path.read_text(encoding="utf-8")
    assert old in t, f"fixture text not found in {path.name}: {old[:60]!r}"
    path.write_text(t.replace(old, new, 1), encoding="utf-8")


# Each case mutates a copy, then expects that rule id in the output.
CASES: dict[str, callable] = {}


def case(rule):
    def deco(fn):
        CASES[rule] = fn
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
def _(r): sub(r / "image-registry/routes.yaml", "chain: [image-review, image-refine]",
              "chain: [image-review, image-nonexistent]")


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
    f = r / f"{S}_image/CONTRACT.md"
    f.write_text(f.read_text(encoding="utf-8").replace("asserted", "claimed"), encoding="utf-8")


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



@case("V34")
def _(r):
    """Reachable and runnable must move together, whichever way they are split."""
    for d in sorted((r / "skills").glob("image-*")):
        link = d / "refute.py"
        if link.is_symlink():
            link.unlink()                      # runnable, and now out of reach
            return
    # No set-wide link to remove: make a skill runnable instead, and leave it
    # unreachable. Widening a class trips V15 too, which the harness allows —
    # it only asks that V34 appear.
    sub(r / "image-registry/harness.yaml",
        "tools: \"Read, Grep, Glob, Write", "tools: \"Read, Grep, Glob, Bash, Write")


@case("V34-decoration")
def _(r):
    """A link where the class grants no shell reads like a capability and is not one."""
    import yaml as _y
    caps = _y.safe_load((r / "image-registry/capabilities.yaml").read_text())
    cls = _y.safe_load((r / "image-registry/harness.yaml").read_text())["permission_classes"]
    for name, e in caps.items():
        if "Bash" not in cls[e["class"]]["tools"]:
            (r / "skills" / name / "refute.py").symlink_to("../../image-tools/refute.py")
            return
    for d in sorted((r / "skills").glob("image-*")):
        link = d / "refute.py"
        if link.is_symlink():
            link.unlink()
            link.symlink_to("../../image-tools/render.py")   # the set's own, but the wrong tool
            return


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
              "it is `IRREPRODUCIBLE` regardless", "it cannot be repeated regardless")


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


def main() -> int:
    baseline = run(ROOT)
    if "green" not in baseline:
        print("the working tree is already failing; fix that first:\n" + baseline)
        return 1

    bad: list[str] = []
    for rule, mutate in CASES.items():
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "repo"
            shutil.copytree(ROOT, copy, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            mutate(copy)
            out = run(copy)
            expect = rule.split("-")[0]
            if not re.search(rf"^\s*{expect}: ", out, re.M):
                bad.append(rule)
                print(f"  {rule} did not fire\n{out}")

    print(f"{len(CASES)} rules exercised, {len(bad)} silent")
    if bad:
        print("silent: " + ", ".join(bad))
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
