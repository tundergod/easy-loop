#!/usr/bin/env python3
"""Layer 1: mechanical consistency checks for the easy-loop skill.

No LLM, no dependencies (stdlib only, Python >= 3.9). Run on every edit:

    python3 evals/lint.py

Exit 0 = clean, exit 1 = findings (printed one per line).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "easy-loop"
FINDINGS: list[str] = []


def find(msg: str) -> None:
    FINDINGS.append(msg)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# --- frontmatter -----------------------------------------------------------
skill_md = read(SKILL / "SKILL.md")
m = re.match(r"^---\n(.*?)\n---\n", skill_md, re.S)
if not m:
    find("SKILL.md: missing frontmatter block")
    fm = {}
else:
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"')

name = fm.get("name", "")
if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
    find(f"frontmatter name invalid: {name!r}")
if name != SKILL.name:
    find(f"frontmatter name {name!r} != directory name {SKILL.name!r}")
desc = fm.get("description", "")
if not desc or len(desc) > 1024 or re.search(r"<[^>]+>", desc):
    find("frontmatter description empty, >1024 chars, or contains XML tags")

body_lines = skill_md[m.end():].count("\n") if m else 0
if body_lines > 500:
    find(f"SKILL.md body is {body_lines} lines (> 500)")

# --- file references resolve ------------------------------------------------
md_files = sorted(SKILL.rglob("*.md"))
for f in md_files:
    for ref in re.findall(r"`(references/[a-z-]+\.md|guideline\.md|loops\.md)`", read(f)):
        if not (SKILL / ref).exists():
            find(f"{f.relative_to(ROOT)}: dangling reference `{ref}`")

# --- envelope field consistency ---------------------------------------------
proto = read(SKILL / "references" / "loop-protocol.md")
env_block = re.search(r"```text\nrole:.*?```", proto, re.S)
if not env_block:
    find("loop-protocol.md: envelope block not found")
    env_fields = set()
else:
    env_fields = set(re.findall(r"^([a-z_]+):", env_block.group(0), re.M))
    env_fields.update({"allowed_paths", "forbidden_ops"})  # combined line

for f in md_files:
    for field in re.findall(r"envelope's `([a-z_]+)`", read(f)):
        if field not in env_fields:
            find(f"{f.relative_to(ROOT)}: envelope field `{field}` not in protocol envelope")

# --- enum coverage -----------------------------------------------------------
state_statuses = {"running", "awaiting_approval", "done", "failed", "cancelled"}
for s in state_statuses:
    if s not in proto:
        find(f"loop-protocol.md: state status `{s}` never mentioned outside schema")

routing = re.search(r"## Status Routing.*?```text\n(.*?)```", proto, re.S)
routing_txt = routing.group(1) if routing else ""
for s in ["PASS", "FAIL", "CONTRACT_INVALID", "NEEDS_USER", "BLOCKED"]:
    if s not in routing_txt:
        find(f"loop-protocol.md Status Routing: no rule for `{s}`")

kind_m = re.search(r'"kind": "([^"]+)"', proto)
if kind_m:
    kinds = [k.strip() for k in kind_m.group(1).split("|")]
    mapping_para = proto.split("The runner sets `kind`", 1)
    mapping = mapping_para[1][:800] if len(mapping_para) > 1 else ""
    for k in kinds:
        if f"`{k}`" not in mapping:
            find(f"loop-protocol.md: kind `{k}` has no entry in the kind-mapping paragraph")
else:
    find("loop-protocol.md: pending_approval kind enum not found")

# --- known-stale tokens -------------------------------------------------------
for f in md_files + [ROOT / "README.md"]:
    txt = read(f)
    for stale in ["role-manager", "needs_approval"]:
        if stale in txt:
            find(f"{f.relative_to(ROOT)}: stale token `{stale}`")

# --- injection table names role files that exist ------------------------------
for ref in re.findall(r"`(references/role-[a-z]+\.md)`", proto):
    if not (SKILL / ref).exists():
        find(f"loop-protocol.md injection table: missing {ref}")

if FINDINGS:
    print(f"LINT: {len(FINDINGS)} finding(s)")
    for x in FINDINGS:
        print(f"  - {x}")
    sys.exit(1)
print("LINT: clean")
