### The two lists (interest profile)

Every digest is split in two, and the split is driven by ONE profile shared by every source class:

- **`⭐ might interest you`** — matched items, each line saying *why* (`matched topic: mcp`).
- **`rest`** — everything else, one compact line each. Nothing is silently dropped.

- **One `interests.yaml`, never one per source type.** The same include/exclude engine (topics,
  keywords, language) scores a GitHub repo, a shop flyer and a blog post; source-specific extras hang
  off a `per_source:` key so the shared part stays shared. Tuning the profile once upgrades every
  source — that is the point of the file (the "what I like" list must serve supermarket
  catalogs as well as repos).
- **Matching runs in the collector, deterministically**, and each item is stored *pre-tagged* with its
  score and the rules that fired. Free (no LLM call per item), auditable, and the agentic tier then
  only writes prose and judges borderline items.
- **`exclude` demotes, it never hides**: an excluded item stays visible under `rest`.
- **The profile and the source list are personal data in a PUBLIC repo**: commit
  `interests.example.yaml` / `sources.example.yaml` (schema only) and keep the real files outside git,
  beside the state dir.
