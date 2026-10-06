# Reconciling the two trees (do this BEFORE any cleanup)

`make skills-status` is the authoritative duplicate list (live own-store copies that duplicate a git-managed name);
`make skills-diff` reports per skill `OK` / `DIFFERS` / `MISSING`; `make skills-drift` is the deploy's gate.

- **`MISSING` means "the deploy has not landed", never "redundant".** The own-store copy of a shared name can be the
  only copy the index has — the CLI dedupes by name, so deleting it first makes the skill vanish from the index.
  Order: deploy → confirm `skills-diff` prints no `MISSING`/`DIFFERS` → only then delete the own-store duplicate.
- **Deleting a deployed name locally is a no-op** — the next `make skills-deploy` restores it. Tracks 1/2 are
  deleted by repo PR; say that instead of deleting.
- `make skills-deploy` ABORTS on any `DIFFERS` (by design: it never silently reverts an in-place edit).
  `SKILLS_FORCE=1 make skills-deploy` is the escape hatch and is safe ONLY once the newer live content has been ported
  into the source tree — otherwise it overwrites that content for good.
- **`DIFFERS` never says which side is newer — check per FILE** with `stat -c '%s %y'` on both copies (the drifted set
  is usually mixed). Live strictly newer → port live→source (sanitized). Source strictly newer → port nothing, the
  deploy is the fix. A blanket "reconcile live→git" DELETES the newer source content; a blanket deploy reverts the
  newer live content.
- **When the gate ABORTS, attribute the drift and SHOW the delta before acting on it.** `hermes curator ledger` names
  the pass that patched the live copy and when — a curator/background-review patch minutes after your own deploy is
  the signature, and it means that live content is knowledge, not noise. Then render the delta per drifted skill with
  `scripts/review-drift.py <source-root> <live-root> <skill-dir>…` (writes `drift-<skill>.diff`, classifies the change,
  scrubs the added lines), hand the user the diff files plus what the added lines actually SAY, state which side is
  strictly newer, and recommend — do not force-deploy or port on their behalf. This user reads the delta before
  agreeing to keep it, and a forced deploy discards the passed lesson for good.
- **Classify additions vs a rewrite before copying either way.** Live-only lines with zero source-only lines = pure
  addition, so live→source is lossless. Source-only lines present = the live side rewrote something: read those lines
  before discarding either side — they are often a rule the live version CORRECTED, and restoring a superseded claim
  from the source is worse than the drift you set out to fix.
- **An autonomous rewrite is a PROPOSAL, not a fact — verify its claims against the implementation before publishing
  them into git.** Such a pass writes plausible, well-phrased assertions; run the decisive check (read the guard or
  function it names, or drive the code in a scratch script) and port only what holds, restating it with the scope the
  code actually has. A claim can be directionally right and still wrong in scope — a refusal list that omits
  `external_dirs` and an actor gate both send the next session to the wrong place. Report anything you could not
  verify as unverified instead of merging it on tone.
- Re-run `skills-diff` after the deploy — a clean report is the proof, not the deploy's own output.
