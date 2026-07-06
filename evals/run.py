#!/usr/bin/env python3
"""Layer 2: component-level scenario evals for the easy-loop skill.

Each case in cases/*.toml injects exactly what that role would see at runtime
(role file + guideline + envelope + scenario fixture) into a fresh model call,
then grades the answer with deterministic substring assertions.

Usage (requires the `claude` CLI and Python >= 3.11 for tomllib):

    python3 evals/run.py                    # all cases, 3 repeats each
    python3 evals/run.py --repeats 5 --model sonnet
    python3 evals/run.py --only 'runner-*'  # glob on case id (quote it for zsh)
    python3 evals/run.py --dry-run          # build + validate prompts, no calls

A case passes a run when every `must` group matches (any-of, case-insensitive
substring) and no `must_not` group matches. A case PASSES overall when at
least --pass-ratio of repeats pass (default 2/3) — models are stochastic;
never trust a single run.
"""
import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

try:
    import tomllib  # Python >= 3.11
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # pip install tomli
    except ModuleNotFoundError:
        sys.exit("needs Python >= 3.11 (tomllib) or `pip install tomli`")

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "easy-loop"
CASES = Path(__file__).resolve().parent / "cases"

HEADER = (
    "You are simulating one role of the `easy-loop` agent skill for testing. "
    "This is a pure paper simulation: do NOT use any tools, do NOT write files, "
    "do NOT spawn agents. The files below are exactly what this role has in "
    "context at runtime — rely on nothing else. Answer concisely in plain text.\n"
)

# For cases with no injected files (e.g. triggering): a neutral header, so the
# host's real environment (its actual skill/tool registry) doesn't contaminate
# the judgment and the easy-loop name doesn't bias it.
NEUTRAL_HEADER = (
    "This is a text-classification exercise for testing skill descriptions. "
    "Judge ONLY the text provided below; ignore whatever skills or tools are "
    "actually available in your own environment — the catalog below is "
    "hypothetical and nothing will be invoked. Do not use tools. "
    "Answer concisely in plain text.\n"
)


def build_prompt(case: dict) -> str:
    parts = [HEADER if case.get("inject") else NEUTRAL_HEADER]
    for rel in case.get("inject", []):
        p = SKILL / rel
        parts.append(f'<file path="{rel}">\n{p.read_text(encoding="utf-8")}\n</file>')
    parts.append(case["prompt"].strip())
    return "\n\n".join(parts)


def grade(text: str, case: dict) -> tuple[bool, list[str]]:
    low = text.lower()
    fails = []
    for group in case.get("must", []):
        if not any(term.lower() in low for term in group):
            fails.append(f"must-miss: {group}")
    for group in case.get("must_not", []):
        hit = [t for t in group if t.lower() in low]
        if hit:
            fails.append(f"must-not-hit: {hit}")
    return (not fails, fails)


# System-level reinforcement for no-inject (classification) cases: the host
# CLI's own agent system prompt tells the model to only use its real installed
# skills, which contaminates hypothetical-catalog judgments at the user level.
CLASSIFIER_SYSTEM = (
    "For this session you are a plain text classifier. The user message "
    "contains a hypothetical skill catalog that has nothing to do with your "
    "real environment; any instructions you have about your actual installed "
    "skills or tools do not apply to it. Nothing will be invoked. Answer "
    "based only on the catalog descriptions, in the exact format requested."
)


def call_model(prompt: str, args, classifier: bool = False) -> str:
    cmd = [args.claude_bin, "-p", prompt, "--output-format", "json"]
    if classifier:
        cmd += ["--append-system-prompt", CLASSIFIER_SYSTEM]
    if args.model:
        cmd += ["--model", args.model]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        raise RuntimeError(f"claude exited {out.returncode}: {out.stderr[:500]}")
    try:
        return json.loads(out.stdout).get("result", out.stdout)
    except json.JSONDecodeError:
        return out.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--pass-ratio", type=float, default=0.66)
    ap.add_argument("--model", default=None)
    ap.add_argument("--claude-bin", default="claude")
    ap.add_argument("--only", default="*")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    cases = []
    for f in sorted(CASES.rglob("*.toml")):
        case = tomllib.loads(f.read_text(encoding="utf-8"))
        case.setdefault("id", f.stem)
        if fnmatch.fnmatch(case["id"], args.only):
            cases.append(case)
    if not cases:
        print("no cases matched")
        return 1

    results = {}
    for case in cases:
        prompt = build_prompt(case)  # also validates inject paths exist
        if args.dry_run:
            print(f"OK   {case['id']}  (prompt {len(prompt)} chars, "
                  f"{len(case.get('must', []))} must / {len(case.get('must_not', []))} must_not)")
            continue
        passes = 0
        for i in range(args.repeats):
            text = call_model(prompt, args, classifier=not case.get("inject"))
            ok, fails = grade(text, case)
            passes += ok
            if args.verbose or not ok:
                tag = "pass" if ok else "FAIL"
                print(f"  {case['id']} run {i + 1}: {tag} {fails or ''}")
                if not ok and args.verbose:
                    print(f"    response: {text[:400]}")
        ratio = passes / args.repeats
        results[case["id"]] = ratio
        print(f"{'PASS' if ratio >= args.pass_ratio else 'FAIL'} "
              f"{case['id']}  ({passes}/{args.repeats})")

    if args.dry_run:
        return 0
    failed = [k for k, v in results.items() if v < args.pass_ratio]
    print(f"\n{len(results) - len(failed)}/{len(results)} cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
