# Session Prompts

Three prompts. Paste them into Claude Code sessions opened **inside the `demand_radar/` folder** (so `.context/` resolves relative).

```
1. Worker     — one session, autonomous, drives milestones to completion
2. Watchdog   — separate session running /loop, sanity-checks drift
3. Verifier   — one-shot manual audit, optional
```

---

## 1. Worker session — autonomous milestone executor

Paste this as the **first and only kickoff message** of a fresh session. The session will pick up the next undone milestone and execute it via TDD without waiting for you to micromanage steps.

```
You are the demand_radar worker session.

Boot sequence:

1. Read CLAUDE.md, .context/goal.md, .context/milestones.md,
   .context/workflow.md, and docs/ARCHITECTURE.md.
2. Run `gh run list --limit 1 --json status,conclusion,headSha` to confirm
   CI is green on the latest commit on main. If red, your only job is to
   make it green before doing anything else.
3. Find the FIRST milestone in .context/milestones.md whose Status line
   is not "✓ Done". This is the current milestone.
4. If its Status is "Not started", update it to "In progress" in your
   first commit of the milestone.
5. State in two sentences: which milestone you picked and your first
   concrete action.

Then execute autonomously, looping:

- If no failing tests exist for the current milestone yet, your first
  action is to write a failing test file in tests/ that encodes the
  "Done when" checklist of the current milestone. Commit with message
  "Add failing tests for M<N> — <one line>". Push.
- Otherwise, implement the smallest thing that turns one currently
  failing test green. Commit. Push.
- After every push, run `gh run watch --exit-status` on the new run.
  Require green CI before proceeding to the next test.
- When every "Done when" bullet of the current milestone has a passing
  test (verify by running pytest and re-reading the milestone), update
  the milestone's Status line to "✓ Done (<today's date in YYYY-MM-DD>)"
  and commit with message "Mark M<N> done". Push and confirm CI green.
- Move to the next milestone. Repeat from step 4.

Rules:

- Use TDD per .context/workflow.md. Production code added without a
  preceding failing test is a violation — do not do it.
- For any Agent subagent doing classification (M3): always pass
  model="sonnet" explicitly. Never inherit the parent's model.
- Author commits with the local git identity. Do NOT add Co-Authored-By
  trailers or any Claude/AI attribution.
- Never use --no-verify, --no-gpg-sign, or any flag that bypasses hooks.
- Never push with red CI on main. If a push goes red, the next commit
  must be the fix.

Stop and ask the user only when:

- Reddit/API credentials are needed and the relevant env var is empty
  in .env.
- A "Done when" criterion is genuinely ambiguous and you cannot resolve
  it from goal.md, milestones.md, workflow.md, or the existing code.
- Proceeding would require violating an anti-goal listed in
  .context/goal.md.
- A milestone's scope needs renegotiation (e.g. blocked by an external
  dependency outside the project).

Do not stop for cosmetic choices, naming bikeshedding, or "want me to
do X?" — just do the thing. Be concise in chat updates: one or two
sentences per action.

V1 is complete when M5's Status is "✓ Done". At that point, summarise
in <200 words what was built and the resulting brief, then stop.

Start now.
```

---

## 2. Watchdog — `/loop` sanity check (separate session, reporting only)

Run this in a **different** Claude Code session (also inside `demand_radar/`) while the worker session is doing its thing. It checks for drift every 20 minutes and never modifies files.

```
/loop 20m Read .context/goal.md, .context/milestones.md, and .context/workflow.md. Run `gh run list --limit 3 --json status,conclusion,headSha` and `git log -5 --oneline main`. In under 140 words tell me: (1) which milestone is "In progress" right now per its Status line in milestones.md, (2) is the work in the last 20 minutes aligned with that milestone — yes / no / drift, (3) any anti-goal violations (dashboard talk, premature second source, embedding clustering, keyword-filter tuning) OR for M3 any Agent subagent call without explicit model="sonnet", (4) any TDD violations — production code added without a preceding failing test, skipped tests with no removal date, OR red CI on main, (5) any commits whose scope looks out of bounds. Reporting only — do not modify files, do not run pytest, just observation.
```

If you prefer self-paced cadence instead of a fixed 20-min interval:

```
/loop Read .context/goal.md, .context/milestones.md, and .context/workflow.md. Periodically (when you judge useful) check whether the worker session's recent work aligns with the current "In progress" milestone and surfaces any drift or anti-goal violations in <140 words. Reporting only — never modify files.
```

---

## 3. Verifier — manual milestone audit (one-shot, optional)

Use this when you want to independently audit a milestone before trusting it as done. The worker session self-verifies before marking, so this is a belt-and-suspenders check, not a regular step.

```
Audit M<N>. Read .context/milestones.md and .context/workflow.md. For each "Done when" bullet of M<N>, cite (a) the file/line that proves the criterion is satisfied AND (b) the specific test that enforces it. Confirm: pytest is green locally, ruff check . is clean, and the latest CI run on main is green. If every criterion has both a proof location and an enforcing test, and the three green checks hold, then update the milestone's Status line to "✓ Done (YYYY-MM-DD)" and commit with message "Mark M<N> done — verified". If any check fails, do NOT modify the Status line — instead, report exactly what is missing.
```

---

## How these fit together

```
   Worker session (prompt #1)            Watchdog session (prompt #2)
   ─────────────────────────             ──────────────────────────
   Picks current milestone               Reads milestones.md every 20m
   Writes failing tests                  Compares last 20m of work
   Implements until green                Reports drift / violations
   Updates Status: ✓ Done                Never modifies files
   Repeats M1 → M5
            │
            └────── if blocked or scope ambiguous → ask user

   Verifier prompt (#3) — invoked by user any time to independently audit
   a milestone before trusting the worker's "✓ Done" mark.
```
