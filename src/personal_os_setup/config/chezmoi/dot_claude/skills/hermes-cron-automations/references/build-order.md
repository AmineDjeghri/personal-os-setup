### Build order: one source end to end, then widen

The parts that fail are the parse, the dedupe key and the state update — not the message template.
Prove those on ONE source before wiring a second, or a wrong dedupe key reads as "the other sources
are broken".

1. **Collector first, one source.** Config + parse + state + a `--doctor` that prints per-source
   OK/FAIL. Run it twice by hand: the second run on unchanged input must report *nothing new*. If it
   re-sends, the dedupe key is wrong — fix it before five sources inherit the bug.
2. **Then the agentic tier on that same source**, and confirm one real message lands in the target
   chat. Break one URL on purpose once: the digest must still send, with a health footer naming that
   source. A digest that silently omits a dead source is the failure the design exists to prevent.
3. **Then add sources one at a time** — each a YAML entry plus at most one extractor — repeating the
   two-run check. Honour the user's scoping exactly: "v1: only this source, weekly" means build only that;
   the next source is later work, not a hidden extra in the first pass.
4. **Lead with `--doctor` output** whenever the user asks whether it still works: one command answering
   "which sources are alive" beats a narrative about what the code does.
