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


@quiet("a quoted marker is talked about, not left behind")
def _(r):
    f = r / f"{S}image-prompt/playbooks/structure.md"
    f.write_text(f.read_text(encoding="utf-8")
                 + "\nA marker reads `#" + "TODO(agent): <action>` in a document.\n",
                 encoding="utf-8")


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
