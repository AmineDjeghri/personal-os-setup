---
name: hermes-session-recall
description: Use when recalling past or continued Hermes sessions.
---

# Hermes Session Recall (session_search)

Recovering state from past conversations: where a task left off, what question was pending, what a session's final message said. Triggered by "prompt me again" after an approval timeout, "where did we leave off", or any recall request about earlier sessions.

## Procedure

1. **Discovery first, narrow**: `session_search(query=<distinctive keywords>, sort="newest", limit=3)`. Adaptive detail hydrates the top hit fully with an anchored window around the match — enough to answer most recall questions in one call. `sort="newest"` biases toward "where did we leave off".
2. **To find how a session ENDED, phrase-match the tail**: query for wording the final message would plausibly use ("waiting on you", "your call", "merge it when ready", "what remains"). The hydrated window lands ON the last message — which is the pending question/state you need.
3. **Zoom in** with the scroll shape: `session_search(session_id=..., around_message_id=<match_message_id>, window=N)`. Keep windows small; add `role_filter="user,assistant"` to exclude tool noise.
4. **Re-fire pending prompts**: after an approval/clarify timeout, the user's "prompt me again" means re-present the SAME question — recover its text from the session tail (step 2), then re-issue it promptly. If recovery fails after one or two quick attempts, ask the user plainly what decision they're approving — never silently re-derive a different question.

## When the prior conversation is NOT in this context

A follow-up that reads as a continuation ("write a doc about this", "same branch as before") often arrives in a NEW session created seconds earlier: none of the earlier conversation is in context, and the referring words ("this", "both", "the PR") are unresolvable from the message alone. Resolve the referent before acting on it.

1. **Browse live activity, never infer it**: `session_search()` with no args lists the most recently ACTIVE sessions (started_at / last_active + preview). The session whose last_active is minutes old is the conversation being continued — confirm from its preview, then read or scroll it.
2. **Bound the browse with `after="<date>")`** when several sessions compete. The bound applies to session START, so a long-running session that spans days falls outside a recent bound — drop the filter for those and rank by last_active instead.
3. **Read the tail, then answer**: scroll the found session near its end (a real id from that session; the LAST id of one window re-scrolls forward) and reconstruct what the last exchange actually asked, then act on that — not on the literal wording of the new message.
4. `~/.hermes/sessions/sessions.json` is the **gateway routing index** (session key → active session id), not a session list: the key for the current thread points at the session created moments ago, while the conversation being continued sits under a different key. Use it to resolve a routing key only — never to find "the last conversation".

## Pitfalls

- **Scroll-anchor errors are diagnostics, not dead ends.** "around_message_id N not in session" → N lies outside the session's id range (above its last message). "scroll rejected: anchor lives in the current session lineage" → N is INSIDE this conversation's own lineage (this delivery is a continuation of that session): scrolls there are always rejected — the content is nominally "already in your active context" but a fresh delivery does NOT replay it. On the first in-lineage rejection, stop bisecting and switch to the discovery-phrasing route (step 2).
- **Never bisect for a session's tail with scroll anchors**: each attempt only tells you which side of the range you're on (one message per call), and repeated identical calls trip the harness tool-loop hard stop within ~8 failures. Change strategy on the second rejection, not the eighth.
- **Avoid whole-session reads and wide scroll windows**: a full-session read or a `window=20` scroll spills a ~150–200KB SINGLE-LINE JSON into a cache spillover file. read_file pages by line, so a one-line file is capped at ~100K chars with no way to reach the tail. Keep every `session_search` read narrow (low limit, small window, `role_filter`) — and switch to the DB route below before widening anything.
- **Read the session DB directly, through `sqlite3` in the terminal**: it is approval-free here and returns plain, pre-truncated rows — the cheapest way to get a session's user/assistant timeline, its tail, or a duplicate check. Recipes: `references/state-db-queries.md`.
- **Do not use `execute_code` for session recovery**: it is approval-gated here, so it returns BLOCKED ("timed out without user response") when the user isn't watching, and it must not be retried as-is.
- **A message delivered at a session boundary is stored twice** (once in the session being continued, once in the new one): the same text appearing in two sessions is ONE user message, not a repeat. `messages.id` is global and increasing across sessions — order deliveries by id/timestamp and read the copy owned by the session that holds the current turn.
- **When the user is away, approval-gated tools time out silently**: recovery work should use approval-free reads only (read_file, search_files, session_search discovery/scroll), mirroring the standing rule to use approval-free git ops.

## Related

- `hermes-context-usage` — /ctx and /usage report interpretation (context gauges, NOT session history; don't conflate the two features).
