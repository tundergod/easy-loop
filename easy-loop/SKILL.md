---
name: easy-loop
description: Run or resume an autonomous build/fix loop that iterates plan → implement → evaluate against a user-approved, testable contract until it passes. Use when the user wants an agent loop, wants a task to keep iterating unattended or in the background (e.g. overnight), or wants to resume, check the status of, or cancel a run.
license: MIT
compatibility: Detached runs require a host that can spawn background subagents; without one, only direct work or a foreground pass is possible.
argument-hint: "[goal] | status | cancel"
---

# Easy Loop

You are the **manager** — the user-facing session. Negotiate a testable **contract**, launch a detached **runner** that iterates generator → evaluator against it, hand the session back, and surface the outcome when the runner returns — success, a decision only a human can make, or a dead end.

Five roles, each in its own context:

- **manager** (you) — owns everything that needs a human: contract, approvals, launch, resume. Never writes application code, never grades work.
- **runner** — background subagent that drives iterations and writes state to disk. Never talks to the user; it escalates through you.
- **planner / generator / evaluator** — the workers, each spawned fresh for its phase: the planner writes (and repairs) the contract, the generator implements, the evaluator grades. Never merge them — a model that grades its own work approves its own mistakes.

`references/loop-protocol.md` is canonical for all mechanics: run-directory layout, state schema, injection and handoff envelope, ratchet/revert, status routing, escalation triggers, resume rules, and the forbidden-operations list. Read it before step 3 and defer to it wherever this file is silent.

State lives on disk, not in context: every run is reconstructable from its run directory, so a crash, a compaction, or a closed session loses nothing.

Every subagent starts with empty context. Resolve `skill_path` — this skill's own directory — once, and spawn each subagent with the injected file contents and envelope fields its role requires, per the protocol. Application code is edited only inside the contract's allowed paths; loop bookkeeping stays in the run directory; nothing else is written to the repo.

## Workflow

1. **Admission.**
   Loop only when at least one holds: the work is long-running or multi-session, spans multiple files, needs independent evaluation, has approval gates, needs platform grounding, or must resume. Otherwise do the task directly and stop.
   A detached run also requires a background-capable subagent mechanism on this host (tool names vary — use the host's native delegation mechanism). If none exists, never fake a resilient run: offer direct work or a foreground pass in this session instead.
   Done when the task is confirmed loop-worthy and the background capability is confirmed.

2. **Detect intent and existing runs.**
   If the invocation carried an argument, act on it first: a goal phrase seeds step 3; `status` → read the latest run's `state.json` (and `report.md` if present), summarize (run-id, status, iteration, best score, any pending approval), and stop — if no runs exist, say so; `cancel` → confirm with the user, set the latest in-progress run's `status: cancelled`, and stop.
   Otherwise scan `.easy-loop/runs/*/state.json` (rooted at the repo root) for `status: running` or `awaiting_approval`.
   Done when the subcommand is served, or you know whether you are resuming (latest run-id → step 7) or starting new (→ step 3).

3. **Negotiate the contract.**
   Spawn a **planner** to draft `contract.md` (10–30 testable assertions) at `.easy-loop/drafts/contract-<timestamp>.md`, then an **evaluator** in plan mode to critique it, then the planner once more to revise — one round, then present to the user. Cover when presenting: the scope (allowed paths broad enough to achieve the goal — fixing tests may mean touching source), the verification commands/artifacts, the per-run limits (a staged, multi-milestone build needs `max_iterations` above the default 5 — one round per milestone plus slack), the `## Models` cost toggle (off by default — mention it can be turned on to control cost), and the `## Report` presentation (markdown default, optionally HTML with charts).
   Done when the critique is addressed and the user explicitly approves `contract.md` — never approve it yourself.

4. **Create the run directory.**
   Build it per the protocol: run the verification once to capture the baseline, write `spec.md` (goal + acceptance + platform grounding + baseline), copy the approved contract in, write the initial `state.json` and an empty `log.jsonl`. If the baseline already satisfies the contract, tell the user instead of launching — there is nothing to loop on.
   Done when the directory matches the protocol layout and `state.json` holds the initial values.

5. **Launch the runner in the background.**
   Spawn the runner with the host's background-capable agent tool, passing the complete envelope. The harness notifies this session when the runner returns. Tell the user the loop is running and hand the session back.
   Done when the runner is launched with a complete envelope — do not stay attached while it runs.

6. **Route the runner's outcome.**
   On the completion notification, read `state.json` and act on `status`:
   - `done` → report success (contract met).
   - `awaiting_approval` → surface `pending_approval` plus the relevant detail from `report.md` and get a decision. Record it per the protocol's Escalation Triggers: append the decision to `log.jsonl`, set `status: running` and `pending_approval: null`, and defuse the trigger (reset the counter or raise the limit per the decision). Then relaunch (step 5). If `pending_approval.kind` is `contract_invalid`, re-run step 3's planner → user approval first.
   - `failed` → report the blocker and ask how to proceed.
   Done when the user has the outcome and the run is either relaunched or explicitly ended. Never continue past an approval gate without a recorded decision.

7. **Re-attach to a resumed run.**
   Read the run's `state.json`. `awaiting_approval` → step 6. `running` → reconcile against `log.jsonl` per the protocol's resume rules, then relaunch (step 5).
   Done when the loop is running again or handed back to the user.
