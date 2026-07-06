# easy-loop evals

Two layers. Layer 1 is free — run it on every edit. Layer 2 costs model calls — run it before committing skill changes. Neither ships with the installed skill (`npx skills add` takes only the `easy-loop/` subdirectory).

## Layer 1 — lint (mechanical, no LLM)

```bash
python3 evals/lint.py
```

Checks frontmatter constraints, dangling file references, envelope-field consistency between the protocol and the role files, status/kind enum coverage in Status Routing, and known-stale tokens. Exit 1 with findings on any hit.

## Layer 2 — scenario cases (LLM, deterministic grading)

```bash
python3 evals/run.py --dry-run          # validate cases, no model calls
python3 evals/run.py                    # all cases, 3 repeats each
python3 evals/run.py --only 'runner-*' --repeats 5 --model sonnet --verbose
```

Requires the `claude` CLI on PATH (override with `--claude-bin`) and Python ≥ 3.11. Each case injects exactly what that role sees at runtime — its role file, `guideline.md`, an envelope, and a scenario fixture — into a fresh `claude -p` call, then grades the answer with substring assertions: every `must` group must match (any-of within a group), no `must_not` group may match.

Models are stochastic: a case passes overall at ≥ `--pass-ratio` (default 2/3) of repeats. Never tune the skill against a single run.

## Case inventory

| Case | What it protects |
|---|---|
| trigger-positive-overnight | description fires on unattended/overnight phrasing |
| trigger-negative-typo | admission: trivial tasks don't trigger the loop |
| runner-resume-after-generate | resume: generate done → recompute patch.diff → evaluate; no spurious revert |
| runner-escalate-no-progress | ratchet + counter → escalate at limit, not iterate past it |
| runner-contract-invalid-repair | under-limit repair path: planner, no revert, same iteration, no escalation |
| generator-missing-envelope | incomplete envelope → BLOCKED, never improvise |
| generator-forbidden-dependency | approval-gated dependency → BLOCKED, never silent install |
| evaluator-outputs | writes only eval.json; four statuses; runs verification itself |
| manager-approval-defuses-trigger | approval resets the counter — no escalate/approve infinite loop |
| manager-cancel-subcommand | cancel: confirm, set `cancelled`, don't resume |
| manager-no-fake-detached-run | no background capability → never fake a resilient run |

## Adding a case

Copy any `cases/**/*.toml`. Rules of thumb: inject only the role's real injection set (workers never see the protocol); make the scenario force exactly one correct behavior; write assertions as binary observables (state values, file names, status words), not vibes; and when the model keeps passing trivially, the case is a no-op — sharpen it or delete it.

When a case exposes a real defect, fix the skill files, re-run the case, and keep it as a regression guard.
