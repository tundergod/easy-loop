# Loop Protocol Reference

The operational contract shared by the manager and runner. State lives on disk, not in context, so a run survives a crash, a compaction, or a closed session.

Contents: Run Directory · State Schema · Write Invariant · Ratchet and Revert · Resume · Injection and Handoff Envelope · Model Tiers · Status Routing · Escalation Triggers · Forbidden and Approval-Gated Operations · Reporting · Platform Grounding.

## Run Directory

One directory per run. Application code is edited in place in the repo (within the contract's allowed paths); only loop bookkeeping is confined to the run directory.

```text
.easy-loop/runs/<run-id>/
  spec.md          # goal, acceptance criteria, platform grounding, and the baseline verification result (input)
  contract.md      # binding, user-approved checklist plus verification commands/artifacts
  state.json       # the snapshot — small, rewritten atomically each phase
  log.jsonl        # append-only history — one line per phase result
  report.md        # canonical report; the runner is its sole writer
  report.html      # optional presentation with charts (see Reporting)
  iterations/<NNNN>/
    snapshot/      # copy of allowed-path files, taken before generate (what revert restores)
    plan.md  patch.diff  eval.json
```

Use a sortable `<run-id>` (a timestamp/ULID) so "latest" needs no separate pointer file. The **manager** creates the directory and writes `spec.md`, `contract.md`, the initial `state.json`, and an empty `log.jsonl`. The **runner** creates each `iterations/<NNNN>/` before spawning that round's generator. Contract drafts made during negotiation live at `.easy-loop/drafts/contract-<timestamp>.md` until approved and copied in.

## State Schema

`state.json` is the only file needed to re-orient. Keep it small; read it every turn instead of replaying history. The first runner iteration is `iteration: 1`, `phase: "generate"` (the planner already ran during negotiation; `plan` is only re-entered to revise the contract).

```json
{
  "run_id": "",
  "status": "running | awaiting_approval | done | failed | cancelled",
  "iteration": 1,
  "phase": "plan | generate | evaluate",
  "best_score": -1,
  "no_progress_rounds": 0,
  "contract_invalid_rounds": 0,
  "pending_approval": null
}
```

`pending_approval` is `null` unless `status` is `awaiting_approval`. When set, it is a small object the manager can route without guessing from prose:

```json
{
  "kind": "forbidden_operation | scope_expansion | no_progress | iteration_limit | contract_invalid | needs_user | blocked",
  "summary": "",
  "evidence": "",
  "requested_decision": ""
}
```

The runner sets `kind` from the cause: a forbidden/approval-gated operation → `forbidden_operation`; work needs paths or API changes outside the contract's scope → `scope_expansion`; counter limits → `no_progress`, `iteration_limit`, or `contract_invalid`; a worker's `NEEDS_USER`/`BLOCKED` → `needs_user`/`blocked`. If several causes fire at once, use the first in this list and name the rest in `summary`.

`cancelled` is set only by the manager on user request; cancelled runs are never resumed, and a runner that reads it stops immediately without writing. `best_score` starts at `-1` so a legitimate first score of `0` can still be kept. `log.jsonl` is the append-only audit trail; one object per line:

```json
{"iter": 1, "phase": "evaluate", "actor": "evaluator", "result": "FAIL exit1", "score": 0}
```

## Write Invariant

Append the `log.jsonl` line FIRST, then rewrite `state.json` atomically (temp file + rename). The log is the source of truth; a crash mid-write costs at most a re-run of the current phase.

## Ratchet And Revert

After each evaluate, keep the iteration only if `score > best_score`; then set `best_score = score` and `no_progress_rounds = 0`. Otherwise **revert** and increment `no_progress_rounds` (a round that fails to beat the best — including a staged round that does not land its milestone — is a no-progress round, reverted like any other). When the evaluator returns `CONTRACT_INVALID`, increment `contract_invalid_rounds` instead — no revert, and `iteration` does not advance (the code was never graded; the contract is what gets repaired). Any `PASS` or scored `FAIL` resets `contract_invalid_rounds` to 0.

Order each ratchet strictly: perform the revert (if any), **then** append the `ratchet` line, **then** rewrite `state.json`. The line carries the full post-ratchet snapshot so `state.json` is reconstructable from it and resume never recomputes the decision:

```json
{"iter": 3, "phase": "ratchet", "actor": "runner", "result": "KEEP | REVERT", "score": 0.7, "best_score": 0.7, "no_progress_rounds": 0}
```

Revert restores the allowed-path files from `iterations/<NNNN>/snapshot/` (a plain file copy the runner took before `generate`). This is loop-internal bookkeeping within allowed paths — it is pre-approved and exempt from the approval gate; it uses no git.

## Resume

1. Scan `.easy-loop/runs/*/state.json`.
2. A run with `status: running` or `awaiting_approval` is in progress; if several, take the latest `run_id`.
3. Reconcile: read the last `log.jsonl` line. If it records a *completed* phase, the next phase to run is: after `generate` → recompute `patch.diff` from the working tree vs `snapshot/`, then `evaluate`; after `evaluate` with `PASS` → finalize `status: done` (do not re-run); after `evaluate` with `FAIL` → the ratchet has **not** run yet, so apply it against the pre-ratchet `best_score` in `state.json` — keep the tree if the logged score beats it, else revert from this iteration's `snapshot/` — append the `ratchet` line, rewrite `state.json` from it, then `generate` the next iteration; after a `ratchet` line → rewrite `state.json` from that line (idempotent whether or not the pre-crash run reached the state rewrite) and make the tree match it (`REVERT` → restore this iteration's `snapshot/`; `KEEP` → leave it), then `generate` the next iteration; after `evaluate` with `CONTRACT_INVALID` → apply the `CONTRACT_INVALID` line of Status Routing; after `plan` (a contract repair) → re-run `evaluate` of the same iteration.
4. Before re-running an *interrupted* `generate` (the last line predates its `IMPLEMENTED`), restore the working tree from that iteration's `snapshot/` so the phase is idempotent w.r.t. repo source (artifacts under `iterations/<NNNN>/` overwrite cleanly on their own). Starting the *next* iteration's `generate` takes a fresh snapshot instead (runner loop step 1) — do not restore a prior snapshot there, or a kept improvement is lost.

## Injection And Handoff Envelope

Every subagent starts with empty context — never rely on shared history. Spawn it with (a) the **contents** of the files its role requires, inlined into the prompt, and (b) the envelope fields below. All injected files live under the envelope's `skill_path`.

| Role      | Inject the contents of                                  |
|-----------|---------------------------------------------------------|
| runner    | this file, `references/role-runner.md`                  |
| planner   | `references/role-planner.md`, `guideline.md`            |
| generator | `references/role-generator.md`, `guideline.md`          |
| evaluator | `references/role-evaluator.md`, `guideline.md`          |

```text
role:            runner | planner | generator | evaluator
skill_path:      absolute path to this skill's directory
goal:            the user's goal and clarified requirements (planner)
run_path:        .easy-loop/runs/<run-id>/   (empty during contract negotiation)
contract_path:   .../contract.md   (the draft path during negotiation)
allowed_paths:   from contract.md `## Scope`
forbidden_ops:   the protocol's forbidden list plus contract.md `## Scope` additions
verification:    commands and artifacts from contract.md `## Verification`
limits:          max_iterations, no_progress_rounds, contract_invalid_rounds
model_policy:    off, or the per-role tier map from contract.md `## Models`
report:          presentation choice from contract.md `## Report`
iteration:       N
iteration_path:  <run_path>/iterations/<NNNN>/   (zero-padded; generator, evaluator)
findings:        previous iteration's eval.json content (generator, fix rounds only)
milestone:       which staged milestone to advance this round (generator, staged contracts only)
```

A subagent missing required fields must stop and return `BLOCKED`.

## Model Tiers

Off by default: spawn every subagent with no model override so it inherits the session model. Turn tiers on per run (contract `## Models`) only to control cost. When on, each role names a capability *tier*, not a product name, so the policy stays portable: `strong` (quality-critical reasoning), `balanced` (the workhorse), `fast` (light routing and file work).

Default per-role tiers when on: evaluator `strong` (the quality gate — never cheap), generator `balanced` (runs every iteration, the main cost), planner `strong` when the goal is ambiguous else `balanced`, runner `fast`; the manager inherits the session model. The manager/runner resolves each tier to a concrete model on the current platform when spawning (e.g. on Claude Code: `strong`→Opus, `balanced`→Sonnet, `fast`→Haiku). Reasoning effort is not part of the policy; subagents inherit the session's.

## Status Routing

The runner acts on the status a phase returns:

```text
PASS (evaluator)        -> status done, clear pending_approval; runner writes report.md (plus any `## Report` presentation) and returns
FAIL (evaluator)        -> ratchet + revert; iterate, unless an escalation trigger now fires
CONTRACT_INVALID (eval) -> increment contract_invalid_rounds; if >= limit, escalate (awaiting_approval) for planner revision + user approval; else spawn planner to repair the contract (Verification and Acceptance Checklist only — Goal, Scope, and Required Approvals unchanged; anything more returns NEEDS_USER), then re-run evaluate of the same iteration
NEEDS_USER (any role)   -> escalate (awaiting_approval)
BLOCKED (any worker)    -> escalate (awaiting_approval)
unrecoverable error     -> status failed; return to manager
```

## Escalation Triggers

The runner stops for a human (sets `status: awaiting_approval` and a structured `pending_approval`) only on: a contract-forbidden or approval-gated operation is needed; any phase returns `NEEDS_USER` or `BLOCKED`; `contract_invalid_rounds` ≥ the contract's limit; `no_progress_rounds` ≥ the contract's limit; or `iteration` reaches `max_iterations`. Completion is a `PASS`. The counters and `max_iterations` come from the contract's `## Limits` — defaults, used unless the user overrides them during negotiation: `max_iterations` **5**, `no_progress_rounds` **2**, `contract_invalid_rounds` **2**. (A staged contract needs a higher `max_iterations` — the planner sets it from the milestone count; see `role-planner.md`.)

When the manager records an approval to continue, it must also defuse the trigger before relaunching: append the decision to `log.jsonl` (e.g. `{"actor": "manager", "result": "approved: <decision>"}`), set `status: running` and `pending_approval: null`, and reset the triggering counter or raise its limit per the decision (e.g. zero `no_progress_rounds`, raise `max_iterations`). A relaunch that leaves the trigger armed re-escalates immediately.

## Forbidden And Approval-Gated Operations

The single canonical list. The runner escalates rather than performing any of these; workers receive it via the envelope's `forbidden_ops`:

- commits, branches, pushes, pull requests, creating issues
- `git init`
- installing dependencies or local skills/plugins
- destructive file operations outside the run directory and allowed paths
- public API or data-format changes not already approved in the contract
- high-risk platform operations

## Reporting

`report.md` is the canonical record and the runner is its sole writer (on escalation and on completion); the evaluator supplies findings via `iterations/<NNNN>/eval.json`. Any additional presentation is the user's choice, recorded in the contract's `## Report` (default: markdown only). If the user opts for a richer presentation — e.g. `report.html` with charts (simple SVG/Canvas/HTML) for numeric evidence like score trends or pass/fail rates — the runner produces it alongside `report.md`.

## Platform Grounding

The planner grounds the platform per `guideline.md` (read the official or user-provided guide; establish versions, commands, constraints, unsafe operations, smoke tests) and writes the operative constraints into the contract's `## Verification` Notes — that is the copy the generator and evaluator obey. The manager records the same grounding plus the captured baseline in `spec.md` as the run's provenance; workers never read `spec.md`, so any constraint a worker must follow has to be in the contract. The discipline rule itself lives in `guideline.md` (its Platform Grounding section).
