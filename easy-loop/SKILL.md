---
name: easy-loop
description: Start or resume an autonomous build/fix loop against a testable contract. Use when the user wants to start a new agent loop or resume an in-progress one.
---

# Easy Loop

`/easy-loop` makes this session the **manager**: negotiate a testable **contract** with the user, launch a background **runner** that iterates planner → generator → evaluator against that contract, and return to the user only when the contract is met or something needs a human. You are the manager — follow `references/role-manager.md`.

Two roles, and they cannot be merged — one talks to the user, one runs detached:

- **manager** — this main session. User-facing: contract, approvals, launch, resume. Never writes application code.
- **runner** — a background subagent. Drives iterations, spawns a fresh planner/generator/evaluator each round, writes state to disk, and stops when it needs a human. Never talks to the user.

State lives on disk, not in context: the loop survives a crash or a closed session because every run is reconstructable from its **run directory**. See `references/loop-protocol.md` for the run-directory layout, state schema, ratchet/revert, status routing, and resume rules — you rely on it in steps 1 and 3–6.

Every subagent you spawn starts with empty context. Inject what it needs into its prompt: `guideline.md` (shared discipline), the matching `references/role-*.md`, and the file paths from the run directory. Application code is edited in the repo per the contract's allowed paths; loop bookkeeping stays in the run directory — nothing else is written to the repo.

## Workflow

0. **Admission.**
   Confirm the task is loop-worthy per `references/role-manager.md` (long-running, multi-file, needs independent evaluation, has approval gates, or must resume). If not, do it directly and stop.
   Done when the task is confirmed loop-worthy.

1. **Detect resume vs new.**
   Scan `.easy-loop/runs/*/state.json` (rooted at the repo root) for `status: running` or `awaiting_approval`.
   Done when you know whether you are resuming an existing run (take the latest run-id → step 6) or starting a new one (→ step 2).

2. **Negotiate the contract.**
   Take the user's goal. Spawn a **planner** to draft `contract.md` (a checklist of testable assertions, aim 10–30) into a scratch path, then an **evaluator** in plan mode to critique it, then the planner once more to revise — one round, then present. Agree the per-run limits with the user (`max_iterations`, `no_progress_rounds`, `contract_invalid_rounds`, forbidden operations) and record them in the contract's `## Limits`.
   Done when the evaluator's plan-mode critique is addressed and the user explicitly approves `contract.md`.

3. **Create the run directory.**
   Build it per `references/loop-protocol.md`: run the verification once to capture the baseline result, write `spec.md` (goal + acceptance + that baseline), copy the approved `contract.md`, write the initial `state.json` (`iteration: 1`, `phase: "generate"`, `best_score: -1`, `status: "running"`), and an empty `log.jsonl`.
   Done when the run directory matches that layout and `state.json` holds those initial values.

4. **Launch the runner in the background.**
   Spawn the runner with the Agent tool using `run_in_background: true`, passing the handoff envelope (run path, contract path, allowed/forbidden operations, limits, and pointers to `guideline.md` + `references/role-*.md`). The harness notifies this session when the runner returns. Tell the user the loop is running and you will return only on completion or escalation.
   Done when the background runner is launched with a complete envelope.

5. **Route the runner's outcome.**
   On the completion notification, read `state.json` and act on `status`:
   - `done` → report success (contract met).
   - `awaiting_approval` → surface the pending finding/operation from `report.md`, get a decision, record it, then **relaunch (step 4)** with the updated contract or approval. Not done until relaunched or the user ends the run.
   - `failed` → report the blocker and ask how to proceed.
   Done when the user has the outcome and the run is either relaunched or explicitly ended.

6. **Re-attach to a resumed run.**
   Read the run's `state.json`. If `awaiting_approval` → go to step 5. If `running` → reconcile against `log.jsonl` and continue from the next phase per `references/loop-protocol.md`, then relaunch the runner (step 4).
   Done when the loop is running again or handed to the user.

## Escalation

The runner runs hands-off and stops for a human only on the triggers in `references/loop-protocol.md`. Completion is evaluator PASS on the full acceptance checklist. Anything else, it iterates without interrupting the user.

## Approval Policy

The approval-gated operations are the canonical list in `references/loop-protocol.md`. An approved contract does not waive them — they remain interrupts the runner escalates through the manager.
