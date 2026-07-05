# A Simple Loop Workflow

`easy-loop` is a skill that **runs** a Karpathy-style planner/generator/evaluator loop in a repository.

Invoking `/easy-loop` turns the main session into a **manager**: it negotiates a testable contract with the user, launches a background **runner** that iterates generator → evaluator against that contract (re-planning only when the contract needs repair), and returns to the user only when the contract is met or something needs a human. State lives on disk, so a run survives a crash, a compaction, or a closed session and can be resumed.

## Install

Install it with the Skills CLI:

```bash
npx skills add tundergod/easy-loop@easy-loop -g -y   # -g user-level, -y no prompts
```

Reload the session so the skill is picked up, then confirm it is available by typing `/easy-loop`.

## Usage

In the repo you want to work in:

```text
/easy-loop
```

The manager then:

1. Confirms the task is loop-worthy (otherwise it just does it directly).
2. Negotiates a testable contract with you, sets the per-run limits (and optionally a per-role model policy to control cost — off by default), and asks for your approval.
3. Launches the background runner and hands your session back.
4. Returns only when the contract is met, or to escalate a decision it cannot make alone.

To resume a paused or interrupted run, invoke `/easy-loop` again in the same repo — it detects the in-progress run and continues. You can also pass the goal directly, or a subcommand:

```text
/easy-loop make every test in tests/ pass deterministically
/easy-loop status    # summarize the latest run without resuming it
/easy-loop cancel    # stop the latest in-progress run
```

A typical session:

```text
You:    /easy-loop fix the flaky tests in tests/
Claude: (drafts a contract, has it critiqued, presents it)
        Contract: 14 acceptance items, verification `npm test`,
        scope src/ + tests/, limits 5/2/2, model tiers off,
        markdown report. Approve?
You:    approve
Claude: Loop launched (run 20260705-153500). I'll return when it
        finishes or needs a decision.
        ...
Claude: Contract met after 3 iterations — report in
        .easy-loop/runs/20260705-153500/report.md
```

## What It Touches

Loop bookkeeping is written into the target repo under one run directory:

```text
.easy-loop/runs/<run-id>/
  spec.md  contract.md  state.json  log.jsonl  report.md  report.html (only if you choose it)
  iterations/<NNNN>/{snapshot/, plan.md, patch.diff, eval.json}
```

Contract drafts made during negotiation live under `.easy-loop/drafts/` until approved.

Application code is edited in place only inside the contract's approved allowed paths. Shared discipline and role instructions stay in the skill and are injected into each subagent's prompt at run time, so `easy-loop` must be installed to run a loop.

## Recommended Skills

The role instructions describe *concepts* rather than skill names, which keeps the loop portable. We recommend installing skills whose descriptions match those concepts: when one is present it auto-triggers and hands the subagent stronger, battle-tested instructions, so the loop runs better. When absent, the concept still guides the subagent through its built-in discipline — nothing is required and nothing errors.

| Concept in the role | Role | Example skill it would trigger |
|---|---|---|
| test-first: write the failing test, watch it go red, then fix | generator | e.g. `tdd` |
| prove the work is broken; check the diff against the contract | evaluator | e.g. `review`, `verify`, `code-review` |

They fire by description-match, so installing the skill is enough — no configuration. Draw from any skill set you like — for example, Matt Pocock's at <https://github.com/mattpocock/skills>.

## Model Tiers (cost control)

Model tiers are **off by default** — every subagent inherits your session model, so behaviour is unchanged until you opt in. The loop then assigns each role a capability *tier* rather than a fixed model name, keeping the policy portable across platforms.

**How to turn them on:** there is no separate flag — it lives in the contract. The contract the manager shows you for approval has a `## Models` section set to `off`. Before you approve, just tell the manager to enable it — e.g. *"turn on model tiers"* or *"use a cheaper model for the generator, keep the evaluator strong"* — and approve the revised contract.

- `strong` — quality-critical work (the evaluator — the quality gate; never cheap).
- `balanced` — the workhorse (the generator, which runs every iteration and drives most of the cost).
- `fast` — light routing and file work (the runner).

The manager resolves each tier to whatever the current platform offers. On Claude Code, for example: `strong`→Opus, `balanced`→Sonnet, `fast`→Haiku. Per-subagent reasoning effort is not controllable and always inherits the session.

## Repository Layout

```text
easy-loop/
  SKILL.md
  guideline.md
  loops.md
  references/
    loop-protocol.md
    role-runner.md
    role-planner.md
    role-generator.md
    role-evaluator.md
```

## File Roles

- `easy-loop/SKILL.md`: the manager role and workflow — the skill entry point (the main session *is* the manager).
- `easy-loop/guideline.md`: Karpathy-inspired coding discipline injected into every loop worker.
- `easy-loop/loops.md`: Karpathy loop field notes — the "why" behind the protocol (background reading; never injected).
- `easy-loop/references/loop-protocol.md`: the canonical mechanics — run-directory layout, state schema, injection/envelope, ratchet, status routing, escalation, resume.
- `easy-loop/references/role-runner.md`: background loop driver and escalation rules.
- `easy-loop/references/role-{planner,generator,evaluator}.md`: the per-phase worker instructions injected each iteration.

## License

MIT — see [LICENSE](LICENSE).
