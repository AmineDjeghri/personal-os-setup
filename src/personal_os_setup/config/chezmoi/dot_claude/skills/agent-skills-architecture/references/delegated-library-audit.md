# Delegating a library-wide audit or slimming pass

Triggers: "analyse/shorten/clean up our skills", "find dead skills", any review of the whole library. The delegate
is a coding agent in print mode; the work is read-mostly, so the risk is a wrong or unverifiable answer.

## 1. Scope first, delegate second

- Enumerate roots with the file-search tool, one call per root in parallel. Shell loops over several roots and
  one-shot `python -c`/heredoc parsers can stall on an approval gate (nothing changes, full timeout burned):
  read JSON with `jq`, text with the file tools.
- Partition by origin marker (one content search for `origin:`) into ours vs not-ours (`vendored`+`source:`,
  `hub`, unmarked = shipped, `synced/<uuid>/<name>` = account-synced). Put the exclusion list in the brief.
- Decide the deliverable first: "analyse and suggest" = a **suggestions report**, no edit rights; "apply it" is
  a second run (§5). A repo's `.claude/**` is hard-denied to print mode whatever the flags — hand-edit it.
- One run per tree group, **cwd inside the tree it reads**. Never two delegates on one checkout: a session that
  sees foreign activity in its worktree pauses for a "peer" and writes nothing.

## 2. Brief shape (feed it on stdin — quoting-proof)

1. Role, deliverable, "suggestions only: do not edit, rename or delete anything in the trees".
2. Exact roots/skill names in scope + the OUT-OF-SCOPE list.
3. The cut taxonomy with examples: fixed-problem history (dated "verified on" stories, PR numbers, incident
   narration — keep the corrected rule, cut the story), superseded instructions kept "for reference",
   SKILL.md↔reference duplication, upstream detail transcribed wholesale, prose that should be a bullet,
   references nothing routes to.
4. The must-keep list: triggers, exact commands/paths/flags, pitfalls that still bite, safety rules, standing
   user preferences. Anything unverifiable → mark `REVIEW: unsure`.
5. Output per unit + a final table (`skill | file | action | est. lines saved | reason`), "biggest wins",
   "left alone, and why".
6. **Incremental writing**: append each unit as it finishes — print mode emits nothing on a turn cap or spend
   limit, so this is what makes the run salvageable. Order the brief most-important group first.

## 3. Run mechanics

```
cd <tree-or-group-root> && HOME=<home> <claude-bin> -p "Execute the task in the document on stdin."
  --model <explicit id> --effort high --allowedTools 'Read,Write,Glob,Grep' --permission-mode acceptEdits
  --add-dir <report-dir> --max-turns <sized to the file count> --output-format json < brief.md > run.json 2>&1
```

- `--add-dir <report-dir>` lets print mode write the report outside its cwd. Keep reports in a neutral directory,
  never in a repo or under `.claude/**`. Read `run.json` (`.result`, `.num_turns`, `.is_error`): an error string,
  or one or two turns, means nothing ran.
- Background the run; size `--max-turns` from the file count (each read costs a turn). Probe with one trivial
  real call first — a stored-credentials check reads healthy while the live session is dead.
- **Capture `git status` BEFORE the run and attribute dirt by mtime + diff before blaming the delegate**: a second
  session in the checkout, or the background-review pass patching a live tree, produces dirt the run never caused.
  A diff about a different subject is that session's work — report it as concurrent activity.

## 4. Aggregate before answering

- Answer with the **impact list** (skill → file → action), not the report text; treat findings as claims and
  spot-check the largest proposed deletions against the file.
- **Quote measured numbers, never the plan's estimates**: score the pass on `wc -l` before → after. A shortfall
  against the estimate is usually a rule you kept on purpose — name it rather than padding the cut.
- Say which classes were excluded and which files are affected, so the user can widen scope in one message.

## 5. The apply pass is a SECOND run

- Analysis is read-only; the apply brief carries edit rights and must **re-state the cut taxonomy** (the delegate
  doesn't remember the analysis), the exact in-scope paths, **an explicit allowlist of files that may be deleted**
  + "nothing else", "apply only what the report asks", "never touch `REVIEW: unsure`", and "**match on the
  report's quoted text, never its line numbers**" (skip and record items whose passage is gone).
- **Re-read each file before editing; keep content that appeared after the plan was written.**
- **No dangling pointers:** after any deletion grep the tree for every deleted filename; a surviving reference must
  still be routed from its SKILL.md; a shortened routing line replaces the deleted pointer's line.
- Flags: `--allowedTools 'Read,Edit,Write,Glob,Grep,Bash' --permission-mode acceptEdits` (`Bash` only for `rm` of
  whole files), an append-only log with measured `wc -l` before → after per file.
- One writer per tree at a time: don't hand-edit a checkout while a delegate is live in it.
- **Hand-editing a batch: read each file in the same turn you write it** — the write tool refuses an overwrite of
  content the session hasn't just loaded, and an earlier-turn read doesn't count.
- The apply run must not touch git history; commit/push approval rules are in `AGENTS.md`. If a commit bypassed
  the hook, run the repo's own gate standalone straight after and say so.

## 6. Verify the apply, not the summary

- Check what changed: `git status` in a checkout; `find <root> -newermt "-15 minutes" -type f` in a non-git store
  (anything else listed is another writer).
- **Grep for the must-keep classes instead of trusting "kept"**: the safety rule, the exact-command pitfall, the
  standing preference — a slimming pass fails silently by losing one such line. Re-grep the cruft markers the
  brief targeted; a couple of prose hits are normal, a surviving block is not.
- **Settle "already fixed / now false / covered elsewhere" verdicts by grep before deleting on them.** Re-check the
  file, constant, heading or Make target they name, then cut the stale text **and fix the wrong pointer** it was
  hiding. "Covered elsewhere" is the verdict most often wrong: open the other file and grep for the actual
  sentence — otherwise the cut deletes the only copy.
- A delegate-reported deviation from the plan is reporting correctly; read those lines before accepting numbers.

## 7. An independent verification pass gates the commit

Propose a **second, fresh delegate** for any large automated edit before it is committed.

- **Baseline = the UNCOMMITTED diff** (`git diff`, `git show HEAD:<path>` for originals). The apply log is the
  artefact under audit, not evidence. Ask for a per-file verdict, "content lost that should not have been",
  broken pointers and false statements, and a severity-ordered defect list **plus an `UNVERIFIABLE` bucket**
  (without it a verifier invents findings to fill the format).
- **Never commit, reset or stash while a verifier is live in the checkout** — it deletes the diff it is reading
  and the audit returns confident nonsense. Write nothing in the checkout while any run is live.
- **Ask for truth, not plan-adherence**: re-derive load-bearing claims against the code (a test target's flags, a
  constant a skill names, that repointed anchors and `[[wikilinks]]` resolve, that a deleted file's unique content
  survives somewhere).
- Fix what it can prove (a flattened code block, a route to a name that exists nowhere); hand unverifiable items
  to the user as questions. A non-git store can't be diffed — keep before-counts or copy the tree aside first.
- Re-check invariants yourself afterwards: every `references/` file routed, frontmatter intact, no pointer to a
  deleted file, the loader lists every name.
- **Deploying is its own approval**: editing the source makes the live copy stale (`DIFFERS`, deleted files still
  present). Report that state; never fold the deploy into "applied".
- Budget "audit → fix → commit" as three runs: a verifier over a ~2.8k-line cut found two real losses (each
  deleted on a false "covered elsewhere") that the applier's own log had called faithful.
