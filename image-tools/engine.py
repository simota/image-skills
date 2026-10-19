#!/usr/bin/env python3
"""Run a checker on an engine that did not produce the work.

`routes.yaml` defers every loop route's `checker` to run time, because all three
CLIs read the same SKILL.md and any of them may be the one running. This resolves
it: given the engine that is running, it picks one that is not.

    make engines                     every declared engine answers, or says why
    python3 image-tools/engine.py --running claude --prompt-file p.txt --schema s.json

**The running engine is stated, never sniffed.** codex launched from inside
Claude Code inherits `CLAUDECODE` and `CLAUDE_CODE_*`, so a nested run reads as
its parent and any env heuristic silently mis-identifies it — which would hand
back a verdict from the very engine that was supposed to be excluded. `--running`
is required, and absent it this stops.

**A checker that did not run is not a checker that passed.** Every failure path
here raises. Nothing returns a default verdict, nothing degrades to "assume
fine": an engine missing from PATH, an engine that starts and produces no
parseable object, a response that does not match the schema — each is an error
with the engine's own words attached, because the alternative is a green run
that verified nothing (DESIGN §5.4b).

Engine quirks, re-checked by `make engines` rather than dated:

* `codex exec` rejects a schema without `additionalProperties: false`, at every
  level, and one whose `required` does not list every property. Schemas are
  normalised here so callers write ordinary JSON Schema.
* The prompt goes on stdin for codex and claude, never as an argument: a prompt
  that starts with `-` is read as a flag, and a long one overflows the argument
  list before the engine ever sees it.
* `agy --print` returns an envelope; the validated object is `structured_output`.
* `claude -p --json-schema` validates the object and returns it in the envelope's
  `structured_output`; `result` carries the same object as a string.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
H = yaml.safe_load((ROOT / "image-registry" / "harness.yaml").read_text(encoding="utf-8"))
ENGINES = H.get("engines") or {}
TIMEOUT = 600


class EngineError(RuntimeError):
    """The engine did not answer. Never a verdict."""


# Where a schema holds further schemas. Recursion stays inside these, so a
# `default`, `const`, `enum` or `examples` value that happens to look like a
# schema is data and is left exactly as written.
_SCHEMA_LIST = ("anyOf", "oneOf", "allOf", "prefixItems")
_SCHEMA_ONE = ("items", "not", "if", "then", "else", "contains", "propertyNames",
               "additionalItems", "unevaluatedItems", "unevaluatedProperties",
               "additionalProperties")
_SCHEMA_MAP = ("properties", "$defs", "definitions", "patternProperties",
               "dependentSchemas", "dependencies")


def strict(schema):
    """Every object closed and every property required, at every depth —
    including inside `anyOf`/`oneOf`/`allOf`, list-form `items`, and a nullable
    `type: [object, null]`. That is what codex requires and agy tolerates."""
    if not isinstance(schema, dict):
        return schema
    out = dict(schema)
    for k in _SCHEMA_LIST:
        if isinstance(out.get(k), list):
            out[k] = [strict(v) for v in out[k]]
    for k in _SCHEMA_ONE:
        if isinstance(out.get(k), list):
            out[k] = [strict(v) for v in out[k]]
        elif isinstance(out.get(k), dict):
            out[k] = strict(out[k])
    for k in _SCHEMA_MAP:
        if isinstance(out.get(k), dict):                 # `dependencies` may hold
            out[k] = {n: strict(v) for n, v in out[k].items()}   # lists; strict()
                                                                 # passes those through
    kind = out.get("type")
    if kind == "object" or (isinstance(kind, list) and "object" in kind):
        out["additionalProperties"] = False
        out["properties"] = out.get("properties") or {}
        out["required"] = list(out["properties"])
    return out


_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool,
          "integer": int, "number": (int, float), "null": type(None)}


def _is_type(got, kind: str) -> bool:
    if isinstance(got, bool) and kind in ("integer", "number"):
        return False                       # JSON keeps true apart from 1
    if kind == "integer" and isinstance(got, float):
        return got.is_integer()            # 1.0 is an integer in JSON Schema
    return isinstance(got, _TYPES[kind])


def _same(a, b) -> bool:
    """Equal as JSON values: Python's True == 1 and False == 0, JSON's do not."""
    return (isinstance(a, bool), a) == (isinstance(b, bool), b)


def conforms(got, schema: dict, where: str = "answer") -> list[str]:
    """What is wrong with `got` against the parts of `schema` this set uses:
    `type`, `enum`, `const`, `required`, `properties`, `additionalProperties:
    false` and `items`. Not a full validator — `anyOf` and friends are not
    checked — and not a lenient one either: `"false"` is not a boolean, and
    reading it as one turned a pass into a refutation."""
    wrong = []
    kinds = schema.get("type")
    if kinds is not None:
        kinds = kinds if isinstance(kinds, list) else [kinds]
        ok = any(_is_type(got, k) for k in kinds if k in _TYPES)
        if not ok:
            return [f"{where} is {type(got).__name__}, not {'/'.join(kinds)}"]
    if isinstance(got, float) and not math.isfinite(got):
        return [f"{where} is {got!r}, which JSON does not have"]
    if "enum" in schema and isinstance(schema["enum"], list) \
            and not any(_same(got, v) for v in schema["enum"]):
        wrong.append(f"{where} is {got!r}, not one of {schema['enum']!r}")
    if "const" in schema and not _same(got, schema["const"]):
        wrong.append(f"{where} is {got!r}, not {schema['const']!r}")
    if isinstance(got, dict):
        required = schema.get("required") or []
        for key in required if isinstance(required, list) else []:
            if key not in got:
                wrong.append(f"{where} has no {key}")
        props = schema.get("properties") or {}
        for key, sub in props.items():
            if key in got and isinstance(sub, dict):
                wrong += conforms(got[key], sub, f"{where}.{key}")
        if schema.get("additionalProperties") is False:
            for key in got:
                if key not in props:
                    wrong.append(f"{where} has {key}, which the schema closed out")
    if isinstance(got, list) and isinstance(schema.get("items"), dict):
        for n, item in enumerate(got):
            wrong += conforms(item, schema["items"], f"{where}[{n}]")
    return wrong


def run(engine: str, prompt: str, schema: dict) -> dict:
    """Ask `engine` for one object matching `schema`. Raises rather than guessing."""
    got = _ask(engine, prompt, schema)
    # Checked against what every engine was told: the closed schema, so a key
    # the engine added is an error rather than a stowaway in the verdict.
    wrong = conforms(got, strict(schema))
    if wrong:
        raise EngineError(f"{engine} answered outside the schema: {'; '.join(wrong)}")
    return got


def _ask(engine: str, prompt: str, schema: dict):
    known = ENGINES.get("runs_on") or []
    if engine not in known:
        raise EngineError(f"{engine} is not one of {known}")

    with tempfile.TemporaryDirectory(prefix="image-engine-") as tmp:
        d = pathlib.Path(tmp)
        s = d / "schema.json"
        s.write_text(json.dumps(strict(schema)), encoding="utf-8")
        if engine == "codex":
            out = d / "answer.json"
            argv = ["codex", "exec", "--output-schema", str(s), "-o", str(out),
                    "--sandbox", "read-only", "--skip-git-repo-check", "-"]
            r = _spawn(engine, argv, prompt)
            body = out.read_text(encoding="utf-8") if out.exists() else ""
            if not body.strip():
                raise EngineError(f"codex wrote no answer.\n{_tail(r)}")
            return _parse(engine, body)
        if engine == "claude":
            argv = ["claude", "-p", "--output-format", "json",
                    "--json-schema", json.dumps(strict(schema))]
            r = _spawn(engine, argv, prompt)
            envelope = _parse(engine, r.stdout)
            if "structured_output" not in envelope:
                raise EngineError(f"claude returned no structured_output "
                                  f"(subtype {envelope.get('subtype')!r}).\n{_tail(r)}")
            return envelope["structured_output"]
        if engine == "agy":
            argv = ["agy", f"--print={prompt}", "--output-format", "json",
                    "--json-schema", str(s)]
            r = _spawn(engine, argv)
            envelope = _parse(engine, r.stdout)
            if "structured_output" not in envelope:
                raise EngineError(f"agy returned no structured_output "
                                  f"(status {envelope.get('status')!r}).\n{_tail(r)}")
            return envelope["structured_output"]
    raise EngineError(f"no invocation is known for {engine}")


def _spawn(engine: str, argv: list[str], stdin: str | None = None
           ) -> subprocess.CompletedProcess:
    """Run one engine in its own process group, so that a timeout ends the
    whole tree it started rather than only its first process."""
    try:
        p = subprocess.Popen(argv, stdin=subprocess.PIPE if stdin is not None
                             else subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, start_new_session=True)
    except FileNotFoundError:
        raise EngineError(f"{engine} is not on PATH") from None
    except (OSError, ValueError) as e:       # an argument list too long, a NUL
        raise EngineError(f"{engine} could not be started: {e}") from None
    try:
        out, err = p.communicate(input=stdin, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        _kill_tree(p)
        raise EngineError(f"{engine} did not answer within {TIMEOUT}s") from None
    except (OSError, ValueError, UnicodeError) as e:   # a prompt it cannot be sent
        _kill_tree(p)
        raise EngineError(f"{engine} could not be sent the prompt: {e}") from None
    except BaseException:
        # Its own session is out of reach of the terminal's Ctrl-C, so an
        # interrupt here has to end the tree before it is passed on.
        _kill_tree(p)
        raise
    return subprocess.CompletedProcess(argv, p.returncode, out, err)


def _kill_tree(p: subprocess.Popen) -> None:
    import os
    import signal
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except OSError:
        p.kill()
    for stream in (p.stdin, p.stdout, p.stderr):  # not communicate(): after a
        try:                                      # failed one it cannot be reused
            if stream:
                stream.close()
        except OSError:
            pass
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def _parse(engine: str, body: str) -> dict:
    """The one object the engine answered with. A body that is not a single
    object is searched line by line, and exactly one candidate must remain —
    the only one, or the only one marked `type: result`. Taking the last object
    let a log line printed after the answer replace it."""
    stripped = body.strip()
    try:
        got = json.loads(stripped)
        if isinstance(got, dict):
            return got
    except ValueError:
        pass
    found = []
    for line in stripped.splitlines():
        try:
            got = json.loads(line)
        except ValueError:
            continue
        if isinstance(got, dict):
            found.append(got)
    if len(found) > 1:
        found = [o for o in found if o.get("type") == "result"]
    if len(found) == 1:
        return found[0]
    if not found:
        raise EngineError(f"{engine} printed nothing that parses as an object:\n{body[:400]}")
    raise EngineError(f"{engine} printed several objects and none is marked as the "
                      f"answer:\n{body[:400]}")


def _tail(r: subprocess.CompletedProcess) -> str:
    return "\n".join((r.stderr or r.stdout or "").strip().splitlines()[-6:])


def other_than(running: str) -> str:
    """An engine that is not the one running. Raises rather than falling back."""
    known = ENGINES.get("runs_on") or []
    if running not in known:
        raise EngineError(f"the running engine {running!r} is not one of {known}; "
                          "state it correctly rather than letting this guess")
    for candidate in known:
        if candidate != running:
            return candidate
    raise EngineError(f"{known} leaves nothing to check {running} with")


SELFTEST = {"type": "object", "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"]}


def selftest() -> int:
    """Ask each declared engine for one object. Reachability, not correctness."""
    bad = 0
    for engine in ENGINES.get("runs_on") or []:
        try:
            got = run(engine, "Reply with ok=true and nothing else.", SELFTEST)
        except EngineError as e:
            print(f"  {engine}: UNAVAILABLE — {e}")
            bad += 1
            continue
        print(f"  {engine}: answered {got}")
    known = ENGINES.get("runs_on") or []
    print(f"engines reachable: {len(known) - bad}/{len(known)} of {known}   "
          f"any of them may be the one running")
    # Unreachable is reported, never fatal: a machine without one of these still
    # runs every other check, and a hook that fails on a missing CLI gets removed.
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("engine", nargs="?", help="the checker; omit to resolve from --running")
    ap.add_argument("--running", help="the engine running this harness — required, never guessed")
    ap.add_argument("--prompt-file")
    ap.add_argument("--schema")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.running:
        # Not even with a checker named: the exclusion is what makes it a check.
        ap.error("--running is required: state the engine running this harness")
    known = ENGINES.get("runs_on") or []
    if a.running not in known:
        ap.error(f"--running {a.running!r} is not one of {known}")
    if a.engine is not None and a.engine not in known:
        ap.error(f"{a.engine!r} is not one of {known}")
    if not (a.prompt_file and a.schema):
        print("need --prompt-file and --schema", file=sys.stderr)
        return 2
    try:
        engine = a.engine or other_than(a.running)
        if a.running and engine == a.running:
            raise EngineError(f"{engine} is the engine running this; "
                              "a verdict from it is not a check")
        try:
            prompt = pathlib.Path(a.prompt_file).read_text(encoding="utf-8")
            schema = json.loads(pathlib.Path(a.schema).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"cannot read the prompt or the schema: {e}", file=sys.stderr)
            return 2
        if not isinstance(schema, dict):
            print(f"{a.schema}: a schema is an object, not a {type(schema).__name__}",
                  file=sys.stderr)
            return 2
        got = run(engine, prompt, schema)
    except EngineError as e:
        print(f"{a.engine or 'checker'}: {e}", file=sys.stderr)
        return 1
    print(json.dumps(got, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
