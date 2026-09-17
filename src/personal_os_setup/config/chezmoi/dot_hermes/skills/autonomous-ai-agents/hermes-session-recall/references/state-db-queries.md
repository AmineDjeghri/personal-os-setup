# Direct reads of the Hermes session DB

When `session_search` scroll/read spills (nested session dumps → 200KB+ single-line JSON), read the DB
itself: `~/.hermes/state.db` (= `/config/.hermes/state.db` on the HA addons). Terminal + `sqlite3` is
approval-free in this setup, unlike `execute_code`.

## Rules that keep the output small

- **Always `substr(...)`** the content columns — a single assistant message can embed a whole nested
  session read.
- Collapse newlines so each message stays one line: `replace(coalesce(content,''), char(10), ' | ')`.
- **Never `select *`** and never read a whole session; filter by role first (`role in ('user','assistant')`).
- `messages.id` is **global across sessions** and monotonically increasing → it orders deliveries and
  detects duplicates across sessions. `timestamp` is unix epoch (REAL); render with
  `datetime(timestamp,'unixepoch','localtime')`.
- `state-snapshots/<date>-pre-update/state.db` are pre-upgrade copies, never the live DB.

## Which sessions are most recent

```bash
sqlite3 ~/.hermes/state.db "select session_id, max(id) last_id, count(*) msgs from messages group by session_id order by max(id) desc limit 5;"
```

## Cheap timeline / tail of one session

One line per message, truncated, user+assistant only — enough to see how a session started, what it
asked, and how it ended without reading a single tool payload:

```bash
sqlite3 ~/.hermes/state.db "select id, role, datetime(timestamp,'unixepoch','localtime'), substr(replace(coalesce(content,''), char(10),' | '),1,700) from messages where session_id='<sid>' and role in ('user','assistant') order by id;"
```

Add `tool_name` (and drop the role filter) to see which actions were taken, still capped:

```bash
sqlite3 ~/.hermes/state.db "select id, role, datetime(timestamp,'unixepoch','localtime'), substr(coalesce(tool_name,''),1,40), substr(replace(coalesce(content,''), char(10),' | '),1,300) from messages where session_id='<sid>' order by id;"
```

## Which session owns a message id

Useful when a tool result (spillover, error) quotes an id and you need its conversation:

```bash
sqlite3 ~/.hermes/state.db "select session_id, role from messages where id=<id>;"
```

## Reading a session you were told about

`session_search(session_id=..., around_message_id=...)` remains the right first move for a *bounded*
window: shrink `window` (1–5) after any spill, and prefer re-querying with distinctive tail wording over
scrolling. If the ids come back out of range, the anchor belongs to a different session lineage — check
`max(id)` for that session instead of bisecting.
