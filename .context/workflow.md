# Working method — TDD with CI as the gate

Every milestone in [milestones.md](milestones.md) is shipped via test-driven development. CI (`.github/workflows/ci.yml`) is the gate. Red CI = stop and fix before doing anything else.

## The loop, per milestone

1. **Read** the milestone's "Done when" checklist in [milestones.md](milestones.md). Each bullet is a test specification.
2. **Write the failing tests first.** They encode the Done-when criteria.
3. **Commit the failing tests.** Conventional message: `Add failing tests for M<N> — <one line>`. CI will go red on this commit — that is intentional and OK for one commit window.
4. **Implement the smallest thing** that turns one test green. Don't write code that isn't required to pass a test.
5. **Commit and push.** CI must go green before you move to the next test.
6. **Repeat 4–5** until every Done-when bullet has a passing test.
7. **Refactor** if the code is uglier than it needs to be. Tests stay green throughout.
8. **Mark the milestone done** in [milestones.md](milestones.md) only after running the milestone-completion prompt from [session_prompts.md](session_prompts.md) (#4) and getting all-green verification.

## What "tests" means here

- `pytest` unit and integration tests in `tests/`.
- `ruff check .` clean (lint is part of the gate).
- For M3 (LLM classification): recorded subagent responses as fixtures. **No live LLM calls in CI** — they're non-deterministic and expensive.
- For external HTTP (Reddit, future HN/G2): `httpx.MockTransport` with recorded JSON payloads. **No live network calls in CI.**

## When TDD doesn't apply

These are the exceptions, not loopholes:

- Documentation-only commits (e.g. updates to `.context/*.md`, README, docstrings).
- Lint / style / typing fixes with no behaviour change.
- One-line config tweaks (bumping a dep, env-var rename) where the *existing* tests still cover the surface.
- Throwaway research spikes — but delete the spike code afterwards. Spike code in `src/` is debt.

Everything else gets a failing test first.

## Anti-patterns — don't

- **"I'll add tests after I see if this works."** No. Write the test first. The "see if it works" step is the test going green.
- **"This is too simple to test."** If it's too simple to test, it's too simple to need code. Otherwise, write the test.
- **Disabling a failing test to make CI green** (with `@pytest.mark.skip`, `xfail`, removing assertions, deleting the test, etc.). Never. Either fix the test or fix the code.
- **Adding `@pytest.mark.skip` with no removal date in a comment.** Never. A skipped test is dead code with a misleading green badge.
- **Pushing without running pytest locally first.** Waste of a CI run.
- **Pushing with red CI on `main`.** Stop, fix the red, push, then continue.

## How this connects to the goal

Every test we write is one Done-when criterion that's now mechanically enforced. The V1 goal — *one usable brief in 4 weeks* — survives only if the pipeline is trustworthy. TDD is what makes it trustworthy.

If a brief comes back wrong because the classifier mislabelled a signal, we need to be able to trust that the rest of the pipeline didn't ALSO drift. TDD plus CI gives us that floor.

## Execution model

A **single Claude Code session** drives V1 to completion. The user pastes three messages in order:

1. `/goal <V1 completion condition>` — the harness auto-continues turns after each one until the condition evaluates true, then auto-clears.
2. `/loop 20m <drift-check prompt>` — fires periodic sanity-check turns in the same session.
3. The worker boot prompt — kicks off the first work turn.

See [session_prompts.md](session_prompts.md) for the exact text. The worker's loop, per milestone:

1. `git pull` (if multi-machine).
2. `uv run pytest && uv run ruff check .` — both must be green locally before starting a new test.
3. Read the current milestone in [milestones.md](milestones.md) (first one with `Status:` not `✓ Done`).
4. If no failing tests exist for it yet, write the failing test file that encodes its Done-when checklist. Commit. Push.
5. Implement the smallest thing that turns one currently-failing test green. Commit. Push.
6. `gh run watch` — require CI green before the next test.
7. When every Done-when bullet has a passing test, update the milestone's `Status:` line to `✓ Done (YYYY-MM-DD)`. Commit. Push.
8. Move to the next milestone. Repeat from step 3.

If CI ever goes red, the next commit must be the fix. No new features on top of red CI.

The worker stops only when (a) M5 is `✓ Done` (V1 complete), or (b) it hits one of the explicit stop conditions in prompt #1 (missing credentials, ambiguous criteria, anti-goal collision, scope renegotiation).

## See also

- [goal.md](goal.md) — what we're aiming at.
- [milestones.md](milestones.md) — the ordered chunks of work and their Done-when checklists.
- [session_prompts.md](session_prompts.md) — prompts to load this context in new sessions and check drift.
