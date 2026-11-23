# Own-store maintenance recipes

## A skill's category is its path, not its frontmatter

`tools/skills_tool.py::_get_category_from_path` derives category from the first path component:
`<root>/<category>/<skill>/SKILL.md` → that category; a flat `<root>/<skill>/SKILL.md` → blank
category. Re-filing a skill between categories in the own store is a plain `mv`; for a git-managed
skill the repo path IS the category, so it's `git mv` in the source tree followed by a redeploy
(moving only the live copy comes back as `MISSING`/`DIFFERS` on the next diff). Category also forms
part of the address used in some config references (`category/skill`), so a rename can invalidate a
config entry pointing at the old address — check for that before renaming a promoted skill.

## Merging a duplicate: pick the survivor, then prove the fold

**Verify the fold against the LOSER, item by item: a folded body reads fine
with rules missing and a delegated merge drops whole sections silently, so a clean diff proves nothing about lost
content.** Method and the phrase sweep: `reviewing-a-rewrite.md`.

## Shortening a skill that has grown verbose

Skills carry a size norm — **~200 lines for a complex SKILL.md, ~100 for a simple one** — so a 400+-line file is a
compliance failure, not thoroughness, and this user will ask for it to be shortened. Shrink by MOVING, never by
deleting: cut whole sections at their headings, append them verbatim to `references/<topic>.md`, leave a 3-6 line
pointer naming what the reference covers and its path, and register it in the References list. A pointer that
paraphrases a rule instead of pointing at it silently rewrites the skill — keep pointers to coverage + filename,
and carry over only the one hard rule a caller must not miss. Prove the trim with the same phrase sweep as a merge,
run against the PRE-trim text (`git show HEAD:<path>`), and report the line/byte before-and-after with the miss
count.
