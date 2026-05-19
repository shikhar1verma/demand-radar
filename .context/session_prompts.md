# Session Prompts

Paste these into a new Claude Code session opened **inside the `demand_radar/` folder** (so `.context/` resolves relative).

---

## 1. Session-start prompt (load the goal)

Run this as the **first message** of any new session working on demand_radar:

```
Read .context/goal.md, .context/milestones.md, and .context/workflow.md.
Also read CLAUDE.md and docs/ARCHITECTURE.md.

Then in under 150 words tell me:
1. Which milestone (M1–M5) is the current focus, and why.
2. The single next concrete step toward it — which must be either
   (a) writing the next failing test, or (b) implementing the smallest
   thing that turns one current failing test green. Per .context/workflow.md.
3. Any anti-goal drift you see in the current codebase or in my recent
   messages (compare against the anti-goals list in .context/goal.md).

Confirm CI is green by checking `gh run list --limit 1` before suggesting
any new work.

Do not write any code yet. Wait for me to pick the step.
```

---

## 2. Loop check-in prompt (use with `/loop`)

This is the **periodic sanity check**. Wire it via the `/loop` skill so it runs every 20 minutes (or whatever cadence feels right):

```
/loop 20m Read .context/goal.md, .context/milestones.md, and .context/workflow.md. Then read the recent conversation and any git diff since the last check. In under 140 words tell me: (1) which milestone we are currently on, (2) is the work in the last interval aligned with that milestone — yes / no / drifting, (3) any anti-goal violations (dashboard talk, premature second source, embedding clustering, keyword-filter tuning, AND for M3: any Agent subagent call without explicit model="sonnet"), (4) any TDD violations per .context/workflow.md — production code added without a preceding failing test, skipped tests with no removal date, OR red CI on main, (5) the single next concrete step. Reporting only — do not modify files.
```

If you prefer self-paced (model decides when to check in):

```
/loop Read .context/goal.md and .context/milestones.md. Periodically check whether the conversation is aligned with the current milestone and the anti-goals. Surface any drift in <120 words. Reporting only.
```

---

## 3. Manual sanity-check prompt (no /loop, paste when you want it)

When you want a one-shot check without a scheduled loop:

```
Sanity check. Read .context/goal.md and .context/milestones.md. Tell me in under 100 words: which milestone am I on, am I drifting, what is the very next concrete step.
```

---

## 4. Milestone-completion prompt

When you think a milestone is done — use this to validate before crossing it off:

```
I think M<N> is done. Read .context/milestones.md and .context/workflow.md. Verify against the "Done when" checklist. For each criterion, cite the file/line that proves it AND the test that enforces it (or say "not yet" and what's missing). Also confirm: pytest is green locally, ruff check is clean, latest CI run on main is green. Do not mark anything done unless every criterion is satisfied AND there is a test enforcing each one.
```

---

## Tips

- Always start a session with prompt **#1** before doing any work.
- Run prompt **#2** in the background of long sessions so drift gets caught early.
- Use prompt **#4** before pushing a milestone-closing commit — better to find a gap before commit than after.
- If a sanity check says "drifting" twice in a row, **stop coding** and re-read [.context/goal.md](goal.md).
