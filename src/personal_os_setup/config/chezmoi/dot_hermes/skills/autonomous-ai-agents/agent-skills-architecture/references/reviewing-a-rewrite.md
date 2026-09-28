# Reviewing a rewrite the user pushed

When the user rewrites the library themselves and pushes it for review, audit the DIFF, not just the result: the old
side is where the lost knowledge is, and a rewrite can only be called lossless against its baseline.

1. **Find the ref that carries it** (the pushed work may not be on `main`) and read the deletions:
   `git log --oneline HEAD..origin/<branch>`, `git log --diff-filter=D --name-only <range>`,
   `git show HEAD~N:<path>`. Read the removed files before judging anything gone.
2. **Cross-reference sweep, by NAME, over every surface:** other skills' bodies, frontmatter `related_skills`,
   the repo `AGENTS.md` index rows, README/nav lists, and `make help`-style blocks that grep a file by name. The
   name of each deleted or renamed skill is the highest-yield grep in the whole pass.
3. **Structural checks:** frontmatter `name` equals the directory name; every skill dir holds a SKILL.md; the
   `.agents/skills` symlinks resolve (`find .agents/skills -type l ! -exec test -e {} \; -print`); every
   supporting-file reference resolves (both path bases — see the SKILL.md pitfalls).
4. **Live vs source inventory:** store names no source tree holds (orphans — remove by hand, the deploy never
   deletes) and source names with no live copy (`MISSING` — deploy them, never call them redundant).
5. **Privacy-scan only the files the push touched** (`git diff --name-only <range>`). A repo-wide scan drowns the
   real hit under the user's own CHANGELOG/CONTRIBUTING credits and LAN-IP docs, and reports noise as findings.
6. Report per item: file:line, what is wrong, the fix, severity — and mark anything unconfirmed as unverified.

## Delegating the review or the edit

The brief must carry the baseline ref (`git show`/`git log --diff-filter=D` for the removed files), the explicit
out-of-scope list, and the instruction to write findings incrementally — without the baseline the delegate can only
judge what survives, never what was lost. Two tool behaviours to design around:

- **A goal or context containing angle-bracket placeholders is refused outright** ("unexpanded template marker"):
  write literal absolute paths and real values, never `<path>`/`<operation name>`-style hints.
- **Fan out one child per FILE, never per step**, and give every child the SAME machine-checkable invariant
  (e.g. "the count of moved commands must be identical before and after"). Children must not run `git`, `make`, or
  any deploy; the parent re-runs the invariant itself, and any deploy waits until every child has reported — a child
  still writing while the deploy runs publishes a half-edited skill. Judge the invariant on counts the child
  controls, and settle a flagged loss by READING the file, never by grepping its prose: a rewrite rewords the
  surrounding sentences, so literal prose matches report content as missing that is only rephrased.
