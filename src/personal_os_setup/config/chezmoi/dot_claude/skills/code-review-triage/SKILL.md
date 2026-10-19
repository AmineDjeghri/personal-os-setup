---
name: code-review-triage
description: "Use when acting on a review finding on your own code."
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Triaging a review finding on your own code

## When to Use

- A bot, linter or human flags `<file>:<line>` and proposes a fix, forwarded with "can you check this" / "want a
  quick patch adding X?".
- You notice a defect in a sibling script while working on one the user flagged.

The job is **not** to apply the suggestion: decide whether the claim is true, how much it matters *in this
script's run context*, and what the right patch is — then offer it. Reply order: verdict on the claim, priority,
the defects the reviewer missed, then the patch. A patch offered before the verdict reads as agreement.
(Reviewing someone else's PR: `github-code-review`.)

## 1. Verify the claim at the cited line

- Confirm the line number, the actual call, and **what already protects it**. Findings routinely ask for
  protection that exists — a bare `except Exception` is not a "missing exception handler". Say so rather than
  adding a redundant layer.
- An exception handler bounds a **failure**; a timeout bounds a **hang**. A bare `except` never bounds a hang and
  a missing timeout never raises. Check which one the claim is about.

## 2. Grade severity by run context, in one clause

- Interactive, human-watched, one-shot script (a registration helper, a manual sync): a hang is **low**. The same
  defect in a pipeline, cron job or unattended script is **high**. The user decides whether to spend effort on "low".
- "The claim is accurate" is not "the finding is right": if it is mis-prioritized or incomplete, lead with that.

## 3. Find the real unbounded wait before patching

- The flagged line is rarely the worst. Scan the file for `while`, poll/retry loops and recursion: an unbounded
  poll for an external event (a button press, a device coming online) with no attempt cap strands the user, and a
  line-oriented reviewer can't see it.
- Bound it three ways: an attempt cap whose comment states the wall-clock budget, the request exception caught
  *inside* the loop, and a **distinct message for exhaustion** (the same text as an explicit refusal makes the
  operator retry the wrong thing).

## 4. Match the sibling file's value, not the reviewer's number

- Grep neighbouring scripts for the same call class and reuse the literal in use (`timeout=5`) even when the
  finding proposes another (`10`). Then sweep the whole folder for the *same* unguarded call and fix them in one
  pass, reporting how many so the count gap between finding and patch is explained.
- Count **call sites**, not string occurrences: `except requests.exceptions.*` matches the same grep. Report the
  real ratio ("7 of 7 call sites timed").

## 5. Patch minimally, verify by experiment

- Keep the file's style (print-based diagnostics stay print-based; no logging framework for one change).
- Run the compile/lint gate **and** one behavioural probe: point the base URL at a non-routable address and time
  the call, proving the timeout fires in seconds. A syntax check proves nothing about a hang.
- Show the diff and say it is local; "yes, patch it" is not "yes, commit it" (`coding-workflow` § 2).

## Pitfalls

1. **Applying the suggestion because it is plausible.** Both the proposed value and the mechanism are claims; the
   mechanism is usually the wrong part (`except` instead of `timeout`; "hangs indefinitely" where the real cap is
   the OS connect timeout).
2. **Answering "is it right?" with only "yes" or only a patch** — the finding's own gap is part of the answer.
3. **Patching the flagged line and stopping** — the siblings get flagged next.
4. **Editing a file the user is working on.** Check `git status` and open worktrees; land the patch in the
   checkout whose branch owns that path, never in two.
