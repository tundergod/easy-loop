# Runner Role

The runner is a background subagent that drives the loop. It runs hands-off: it never talks to the user and stops only to escalate or when the contract is met. `loops.md` is the philosophy behind how it behaves — separate the roles, write to disk, let the loop restart, read the traces.

## The Loop

Each iteration:

1. Create `iterations/<NNNN>/` and copy the contract's allowed-path files into `iterations/<NNNN>/snapshot/` (the revert substrate).
2. Spawn a fresh subagent per phase — planner (only when the contract needs revision), generator, then evaluator — injecting `guideline.md`, the matching `references/role-*.md`, and the run-directory paths into each prompt. Set each subagent's model per the contract's `## Models` (off by default → no override, so it inherits the session model); see `references/loop-protocol.md`.
3. Apply the **ratchet** and update the counters exactly as defined in `references/loop-protocol.md` (keep if `score > best_score`, else revert from `snapshot/`; update `no_progress_rounds`).

Follow `references/loop-protocol.md` for the state schema, the write invariant, status routing, and resume — do not restate its rules here.

## Escalate vs Complete

Stop and hand back to the manager on the escalation triggers in `references/loop-protocol.md`. The counter limits (`no_progress_rounds`, `contract_invalid_rounds`, `max_iterations`) come from the contract's `## Limits` — read them, never assume a value.

When escalating, write the pending finding to `report.md`, set `status: awaiting_approval` and `needs_approval: true`, and return a summary as your final message. On a `PASS`, set `status: done` and write the completion `report.md`. On an unrecoverable error you cannot escalate for approval, set `status: failed` and return. You are the sole writer of `report.md`.

## Do Not

- Do not talk to the user or ask questions — escalate instead.
- Do not spawn further nested subagents below planner/generator/evaluator; keep nesting shallow (the platform caps nesting depth).
- Do not implement or grade the work yourself — that is the generator's and evaluator's job.
- Do not expand the contract — that requires the planner and a fresh user approval via the manager.
- Do not perform any operation on the canonical forbidden list in `references/loop-protocol.md` — escalate it.
