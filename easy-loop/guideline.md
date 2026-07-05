# Shared Discipline

Karpathy-inspired coding discipline, injected into every loop worker. Operational mechanics live in your envelope and role instructions; this file is discipline only. When a rule says *stop*, stop by returning your role's escalation status — never by guessing.

### Read Before You Write

The biggest source of bad model-written code is writing before reading the codebase. Read the files you are about to touch — read, not skim. Copy the patterns that already exist, and check the imports for what the project actually depends on, so you do not reach for axios where everything is fetch. When you cannot find a pattern, stop instead of guessing.

### Think Before You Code

State your assumptions before typing ("add authentication" is five different things — name the one you picked) and name the tradeoffs. If something is genuinely confusing, stop rather than fill the gap with plausible-looking code; that is exactly the code that passes a casual review and fails when it matters.

### Simplicity

Write the minimum code that solves the problem in front of you now, not every future version of it. Resist premature abstraction, skip error handling for errors that cannot occur, and hardcode values until there is a real reason to configure them. If the only reason something is abstracted is "in case we need to," it is over-built.

### Surgical Changes

Your diff should be as small as the task allows. Do not touch what you were not asked to touch, match the existing style, and never reformat — a formatter pass buries the three lines that matter inside three hundred that do not. Justify every changed line by the task; a "while I was in there" line gets reverted.

### Verification

When fixing a bug, write the failing test first, watch it go red, then fix it — the only proof you fixed the cause and not the symptom. Test behavior that can actually break, not that a constructor sets a field. If something is hard to test, that is information about the design, not permission to skip it.

### Debugging

Investigate; do not guess. Read the whole error and the stack trace, reproduce the problem before you change anything, and change one thing at a time. Do not paper over an unexpected null with a null check; find out why it is null, or the bug just moves somewhere quieter.

### Dependencies

Every dependency is permanent code you do not control. Prefer what the project or the standard library already does (crypto.randomUUID() over a uuid package). In this loop, installing dependencies is approval-gated — escalate, never install silently.

### Failure Modes

Catch yourself in the Kitchen Sink (restructuring half the codebase while you are at it), the Wrong Abstraction (abstracting before the second copy-paste), the Optimistic Path (the happy path handled and the 500 ignored), or the Runaway Refactor (a fix cascading across files) — and stop; do not push through.

### Platform Grounding

If work depends on a real machine, simulator, emulator, SDK, benchmark harness, firmware tool, or cloud platform, first read the official or user-provided guide and record the relevant commands, constraints, versions, unsafe operations, and smoke tests. If no reliable guide exists, stop and recommend creating platform guidance before implementation. Never invent commands or interpret experimental results from memory.
