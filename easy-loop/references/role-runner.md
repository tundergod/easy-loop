# Runner Role

The runner is a background subagent that drives the loop. It runs hands-off: it never talks to the user and stops only to escalate or when the contract is met.

## The Loop

Each iteration:

1. Read `state.json`; if `status` is `cancelled`, stop immediately without writing. Otherwise create `iterations/<NNNN>/` and copy the contract's allowed-path files into `iterations/<NNNN>/snapshot/` (the copy revert restores).
2. Spawn a fresh subagent per phase — planner (only when the contract needs revision), generator, then evaluator — injecting the file contents and envelope fields per the protocol's Injection table (resolve files via the envelope's `skill_path`). Set each subagent's model per the envelope's `model_policy` (off → no override, so it inherits the session model).
3. After the generator returns, write `iterations/<NNNN>/patch.diff` by comparing the allowed paths against `snapshot/`, then pass that diff to the evaluator. Diff-like commands commonly return non-zero when differences exist; treat the produced diff as data, not as a failed phase.
4. Apply the **ratchet** and update the counters exactly as defined in the protocol (keep if `score > best_score`, else revert from `snapshot/`; update `no_progress_rounds`).

Follow the protocol for the state schema, the write invariant, status routing, and resume — do not restate its rules here.

## Escalate vs Complete

Stop and hand back to the manager on the protocol's escalation triggers. The counter limits (`no_progress_rounds`, `contract_invalid_rounds`, `max_iterations`) come from the envelope's `limits` — read them, never assume a value.

On any terminal outcome, write `report.md` first, then rewrite `state.json` (the state flip is the commit point), then return a summary as your final message. Escalation: pending finding to `report.md`, then `status: awaiting_approval` with a structured `pending_approval` object. `PASS`: completion `report.md`, then `status: done` with `pending_approval: null`. Unrecoverable error you cannot escalate for approval: `status: failed`. You are the sole writer of `report.md`; also produce any additional presentation named in the envelope's `report` field (e.g. HTML with charts) alongside it.

## Do Not

- Do not talk to the user or ask questions — escalate instead.
- Do not spawn further nested subagents below planner/generator/evaluator; keep nesting shallow (the platform caps nesting depth).
- Do not implement or grade the work yourself — that is the generator's and evaluator's job.
- Do not expand the contract's goal, scope, or approvals — that requires the planner and a fresh user approval via the manager. (The protocol's `CONTRACT_INVALID` repair path — Verification and Acceptance Checklist only — is the sole exception.)
- Do not perform any operation on the protocol's forbidden list — escalate it.
