# Easy Loop

`easy-loop` is a skill that **runs** a Karpathy-style planner/generator/evaluator loop in a repository.

Invoking `/easy-loop` turns the main session into a **manager**: it negotiates a testable contract with the user, launches a background **runner** that iterates planner → generator → evaluator against that contract, and returns to the user only when the contract is met or something needs a human. State lives on disk, so a run survives a crash, a compaction, or a closed session and can be resumed.

## Install

`easy-loop` is a skill for Claude Code / Codex. Install it with the Skills CLI:

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

To resume a paused or interrupted run, invoke `/easy-loop` again in the same repo — it detects the in-progress run and continues.

## What It Touches

The only thing written into the target repo is a run directory:

```text
.easy-loop/runs/<run-id>/
  spec.md  contract.md  state.json  log.jsonl  report.md
  iterations/<NNNN>/{plan.md,patch.diff,eval.json}
```

Shared discipline and role instructions stay in the skill and are injected into each subagent's prompt at run time, so `easy-loop` must be installed to run a loop.

## Recommended Skills

The role instructions describe *concepts* rather than skill names, which keeps the loop portable. We recommend installing skills whose descriptions match those concepts: when one is present it auto-triggers and hands the subagent stronger, battle-tested instructions, so the loop runs better. When absent, the concept still guides the subagent through its built-in discipline — nothing is required and nothing errors.

| Concept in the role | Role | Example skill it would trigger |
|---|---|---|
| test-first: write the failing test, watch it go red, then fix | generator | e.g. `tdd` |
| prove the work is broken; check the diff against the contract | evaluator | e.g. `review`, `verify`, `code-review` |

They fire by description-match, so installing the skill is enough — no configuration. Draw from any skill set you like — for example, Matt Pocock's at <https://github.com/mattpocock/skills>.

## Repository Layout

```text
easy-loop/
  SKILL.md
  guideline.md
  loops.md
  references/
    loop-protocol.md
    role-manager.md
    role-runner.md
    role-planner.md
    role-generator.md
    role-evaluator.md
```

## File Roles

- `easy-loop/SKILL.md`: the manager workflow — the skill entry point.
- `easy-loop/guideline.md`: Karpathy-inspired coding discipline injected into every subagent.
- `easy-loop/loops.md`: Karpathy loop field notes — the "why" behind the protocol.
- `easy-loop/references/loop-protocol.md`: run-directory layout, state schema, write invariant, and resume rules.
- `easy-loop/references/role-manager.md`: front-facing controller (main session).
- `easy-loop/references/role-runner.md`: background loop driver and escalation rules.
- `easy-loop/references/role-{planner,generator,evaluator}.md`: the per-phase worker instructions injected each iteration.

## License

MIT — see [LICENSE](LICENSE).
