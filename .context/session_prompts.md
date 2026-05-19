# Session Prompts

**One session.** Three messages to paste in order. The session then runs autonomously until V1 is done — no further user input needed unless the worker hits an explicit stop condition.

```
Message 1: /goal    sets the V1 completion condition; the harness auto-continues
                    turns after each one until this condition is satisfied.
Message 2: /loop    schedules a periodic drift sanity-check (same session,
                    fires every 20 min as its own turn).
Message 3: worker   boots the worker, picks the first non-Done milestone,
                    and starts the TDD loop. /goal carries it forward.
```

Open a Claude Code session **inside `demand_radar/`** (so `.context/` resolves relative), then paste the three messages below in order.

---

## Message 1 — set the V1 goal (`/goal`)

```
/goal All five milestones (M1, M2, M3, M4, M5) in .context/milestones.md have been marked Status "✓ Done (YYYY-MM-DD)" by the worker, and the latest CI run on main has conclusion success.
```

This is the autonomous-continuation condition. After each turn, a small evaluator model checks whether all five milestones are Done and CI is green. If not, it kicks off another turn. If yes, `/goal` auto-clears and the session stops.

---

## Message 2 — enable periodic drift check (`/loop`)

```
/loop 20m Read .context/goal.md, .context/milestones.md, and .context/workflow.md. Run `gh run list --limit 3 --json status,conclusion,headSha` and `git log -5 --oneline main`. In under 140 words tell me: (1) which milestone is "In progress" right now per its Status line in milestones.md, (2) is the work in the last 20 minutes aligned with that milestone — yes / no / drift, (3) any anti-goal violations (dashboard talk, premature second source, embedding clustering, keyword-filter tuning) OR for M3 any Agent subagent call without explicit model="sonnet", (4) any TDD violations — production code added without a preceding failing test, skipped tests with no removal date, OR red CI on main, (5) any commits whose scope looks out of bounds. Reporting only — do not modify files, do not run pytest, just observation.
```

This fires every 20 minutes inside the same session and reports drift. It doesn't modify files; it just surfaces anti-goal/TDD/scope violations as a visible turn.

---

## Message 3 — worker boot prompt

```
You are the demand_radar worker session. /goal is set; the harness will
auto-continue turns until V1 is complete.

Boot:

1. Read CLAUDE.md, .context/goal.md, .context/milestones.md,
   .context/workflow.md, and docs/ARCHITECTURE.md.
2. Run `gh run list --limit 1 --json status,conclusion,headSha` to confirm
   CI is green on main. If red, your only job is to make it green before
   doing anything else.
3. Find the FIRST milestone in .context/milestones.md whose Status line
   is not "✓ Done". This is the current milestone.
4. If its Status is "Not started", change it to "In progress" in your
   first commit of the milestone.
5. State in two sentences: which milestone and your first concrete
   action.

Then execute the TDD loop:

- If no failing tests exist for the current milestone yet, your first
  action is to write a failing test file in tests/ that encodes the
  "Done when" checklist of the current milestone. Commit with message
  "Add failing tests for M<N> — <one line>". Push.
- Otherwise, implement the smallest change that turns one currently
  failing test green. Commit. Push.
- After every push, run `gh run watch --exit-status` on the new run.
  Require green CI before proceeding.
- When every "Done when" bullet has a passing test (verify by running
  pytest and re-reading the milestone), update the milestone's Status
  line to "✓ Done (<today's date in YYYY-MM-DD>)" and commit with
  message "Mark M<N> done". Push, confirm CI green.
- Report in chat: "Marked M<N> ✓ Done. CI green." So the /goal evaluator
  can see progress.
- Move to the next milestone. Repeat from step 4.

Rules:

- TDD per .context/workflow.md. Production code added without a
  preceding failing test is a violation. Do not do it.
- For any Agent subagent doing classification (M3): always pass
  model="sonnet" explicitly. Never inherit the parent's model.
- Author commits with the local git identity. Do NOT add Co-Authored-By
  trailers or any Claude/AI attribution.
- Never use --no-verify, --no-gpg-sign, or any flag that bypasses hooks.
- Never push with red CI on main. If a push goes red, the next commit
  must be the fix.

Stop and ask the user only when:

- Reddit / API credentials are needed and the relevant env var is empty
  in .env.
- A "Done when" criterion is genuinely ambiguous and you cannot resolve
  it from goal.md, milestones.md, workflow.md, or the existing code.
- Proceeding would require violating an anti-goal in .context/goal.md.
- A milestone's scope needs renegotiation (e.g. blocked by an external
  dependency outside the project).

Do not stop for cosmetic choices, naming bikeshedding, or "want me to do
X?" — just do the thing. Be concise: one or two sentences per action.

When M5 is "✓ Done" and CI is green, write a <200-word summary of what
was built and the resulting brief. /goal will auto-clear and the session
will stop on its own.

Start now.
```

---

## How the three messages compose

```
You paste #1 ──▶ /goal sets V1 condition (silent, just enables auto-continue)

You paste #2 ──▶ /loop schedules drift check at 20-min intervals

You paste #3 ──▶ Worker boots, picks M1, starts TDD loop
                  │
                  ├──▶ writes failing test → commits → pushes → gh run watch
                  ├──▶ implements → commits → pushes → gh run watch
                  ├──▶ ... until M1's "Done when" all pass
                  ├──▶ updates Status: ✓ Done (date) → commits → pushes
                  ├──▶ /goal evaluator runs: M1 done but M2–M5 still pending → continue
                  ├──▶ /loop fires at the 20-min mark — reports drift, doesn't modify
                  ├──▶ worker moves to M2, repeats
                  ├──▶ ...
                  ├──▶ M5 marked ✓ Done, CI green
                  └──▶ /goal evaluator: all 5 Done, CI green → condition met → /goal clears
                       Session stops on its own.
```

---

## Verifier — manual one-shot audit (optional, separate invocation)

If you want to independently audit a milestone the worker claims is done — different from the worker's self-verification — paste this any time:

```
Audit M<N>. Read .context/milestones.md and .context/workflow.md. For each "Done when" bullet of M<N>, cite (a) the file/line that proves the criterion is satisfied AND (b) the specific test that enforces it. Confirm pytest is green locally, ruff check . is clean, and the latest CI run on main is green. If every criterion has both a proof location and an enforcing test, and all three green checks hold, update the Status line to "✓ Done (YYYY-MM-DD)" and commit "Mark M<N> done — verified". If anything fails, report what is missing — do NOT modify Status.
```

Use sparingly — the worker self-verifies before marking. This is a belt-and-suspenders spot-audit.

---

## Tips

- **One window is enough.** `/goal` and `/loop` coexist in the same session — `/loop` fires its check as periodic turns, `/goal` evaluates after every turn (including loop turns) for completion.
- **Don't paste all three messages as one block.** Slash commands need their own messages. Paste them in order: #1, wait for ack, #2, wait, #3.
- **If `/goal` auto-clears unexpectedly,** the evaluator thought the condition was satisfied. Inspect `.context/milestones.md` — if it's wrong, re-paste #1 to re-arm.
- **If the worker stops and waits for you,** it hit one of the explicit stop conditions. Answer briefly, the session resumes.
