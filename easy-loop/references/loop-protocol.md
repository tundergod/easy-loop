# Loop Protocol Reference

The operational contract shared by the manager and runner. State lives on disk, not in context, so a run survives a crash, a compaction, or a closed session. Read `loops.md` for the philosophy behind these mechanics.

## Run Directory

One directory per run. Application code is edited in place in the repo (within the contract's allowed paths); only loop bookkeeping is confined to the run directory.

```text
.easy-loop/runs/<run-id>/
  spec.md          # goal, acceptance criteria, and the baseline verification result (input)
  contract.md      # binding, user-approved checklist of testable assertions
  state.json       # the snapshot — small, rewritten atomically each phase
  log.jsonl        # append-only history — one line per phase result
  report.md        # canonical report; the runner is its sole writer
  report.html      # optional presentation with charts (see Reporting)
  iterations/<NNNN>/
    snapshot/      # copy of allowed-path files, taken before generate (revert substrate)
    plan.md  patch.diff  eval.json
```

Use a sortable `<run-id>` (a timestamp/ULID) so "latest" needs no separate pointer file. The **manager** creates the directory and writes `spec.md`, `contract.md`, the initial `state.json`, and an empty `log.jsonl` (workflow step 3). The **runner** creates each `iterations/<NNNN>/` before spawning that round's generator.

## State Schema

`state.json` is the only file needed to re-orient. Keep it small; read it every turn instead of replaying history. The first runner iteration is `iteration: 1`, `phase: "generate"` (the planner already ran during negotiation; `plan` is only re-entered to revise the contract).

```json
{
  "run_id": "",
  "status": "running | awaiting_approval | done | failed",
  "iteration": 1,
  "phase": "plan | generate | evaluate",
  "best_score": -1,
  "no_progress_rounds": 0,
  "contract_invalid_rounds": 0,
  "needs_approval": false
}
```

`best_score` starts at `-1` so a legitimate first score of `0` can still be kept. `log.jsonl` is the append-only audit trail; one object per line:

```json
{"iter": 1, "phase": "evaluate", "actor": "evaluator", "result": "FAIL exit1", "score": 0}
```

## Write Invariant

Append the `log.jsonl` line FIRST, then rewrite `state.json` atomically (temp file + rename). The log is the source of truth; a crash mid-write costs at most a re-run of the current phase.

## Ratchet And Revert

After each evaluate, keep the iteration only if `score > best_score`; then set `best_score = score` and `no_progress_rounds = 0`. Otherwise **revert** and increment `no_progress_rounds`. When the evaluator returns `CONTRACT_INVALID`, increment `contract_invalid_rounds` instead; any `PASS` or scored `FAIL` resets it to 0.

Revert restores the allowed-path files from `iterations/<NNNN>/snapshot/` (a plain file copy the runner took before `generate`). This is loop-internal bookkeeping within allowed paths — it is pre-approved and exempt from the approval gate; it uses no git.

## Resume

1. Scan `.easy-loop/runs/*/state.json`.
2. A run with `status: running` or `awaiting_approval` is in progress; if several, take the latest `run_id`.
3. Reconcile: read the last `log.jsonl` line. If it records a *completed* phase, the next phase to run is: after `generate` → `evaluate`; after `evaluate` with `PASS` → finalize `status: done` (do not re-run); after `evaluate` with `FAIL` → revert, then `generate` of the next iteration.
4. Before re-running any `generate`, restore the working tree from that iteration's `snapshot/` so the phase is idempotent w.r.t. repo source (artifacts under `iterations/<NNNN>/` overwrite cleanly on their own).

## Handoff Envelope

Every subagent starts with empty context. Inject a small structured payload into the prompt — never rely on shared history:

```text
role:            planner | generator | evaluator
run_path:        .easy-loop/runs/<run-id>/
contract_path:   .../contract.md
allowed_paths / forbidden_ops:   ...
iteration:       N
verification:    commands the evaluator runs
```

A subagent missing required fields must stop and return `BLOCKED`.

## Model Tiers

Tiered model selection is **off by default**: spawn every subagent with no model override, so they inherit the session model. Turn it on per run (contract `## Models`) only to control cost.

When on, each role names a capability *tier*, not a product name, so the policy stays portable across platforms:

- `strong` — quality-critical reasoning.
- `balanced` — the workhorse.
- `fast` — light routing and file work.

Default per-role tiers when on: evaluator `strong` (the quality gate — never cheap), generator `balanced` (runs every iteration, the main cost), planner `strong` when the goal is ambiguous else `balanced`, runner `fast`; the manager inherits the session model.

The manager/runner resolves each tier to a concrete model on the current platform when spawning. Example mapping for Claude Code (via the Agent tool `model` parameter): `strong`→Opus, `balanced`→Sonnet, `fast`→Haiku. Per-subagent effort is not controllable on this path and always inherits.

## Status Routing

The runner acts on the status a phase returns:

```text
PASS (evaluator)        -> status done; runner writes report.md and returns
FAIL (evaluator)        -> ratchet + revert; iterate, unless an escalation trigger now fires
CONTRACT_INVALID (eval) -> increment contract_invalid_rounds; if >= limit, escalate (awaiting_approval) for planner revision + user approval; else spawn planner to revise the contract, then continue
NEEDS_USER (any role)   -> escalate (awaiting_approval)
BLOCKED (generator/planner) -> escalate (awaiting_approval)
unrecoverable error     -> status failed; return to manager
```

## Escalation Triggers

The runner stops for a human (sets `awaiting_approval`) only on: `contract_invalid_rounds` ≥ the contract's limit; a contract-forbidden or approval-gated operation is needed; `no_progress_rounds` ≥ the contract's limit; or `iteration` reaches `max_iterations`. Completion is a `PASS`. The counters and `max_iterations` come from the contract's `## Limits` (see `role-planner.md`); token budget is a manager-side advisory ceiling, not a runner auto-trigger, because the runner cannot observe token spend.

## Forbidden And Approval-Gated Operations

The single canonical list. `SKILL.md` and `guideline.md` point here; the runner escalates rather than performing any of these:

- commits, branches, pushes, pull requests, creating issues
- `git init`
- installing dependencies or local skills/plugins
- destructive file operations outside the run directory and allowed paths
- public API or data-format changes not already approved in the contract
- high-risk platform operations

## Reporting

`report.md` is canonical and the runner is its sole writer (on escalation and on completion); the evaluator supplies findings via `iterations/<NNNN>/eval.json`. If `report.md` carries meaningful numeric evidence (score trends, pass/fail rates, timing), render an optional `report.html` with charts (simple SVG/Canvas/HTML) rather than raw tables alone.

## Platform Grounding

Operational note: record the platform's versions, commands, constraints, unsafe operations, and smoke tests in `spec.md` before the generator starts. The discipline rule itself lives in `guideline.md` (section XI).
