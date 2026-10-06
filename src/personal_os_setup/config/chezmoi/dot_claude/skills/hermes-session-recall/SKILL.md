---
name: hermes-session-recall
description: Use when recalling past or continued Hermes sessions.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Hermes Session Recall (session_search)

Recover where a task left off, what question was pending, or what a session's final message said — e.g. after "prompt me again" following an approval timeout, or "where did we leave off".

## Procedure

1. **Discovery first, narrow**: `session_search(query=<distinctive keywords>, sort="newest", limit=3)`. Adaptive detail hydrates the top hit fully with an anchored window around the match — enough to answer most recall questions in one call. `sort="newest"` biases toward "where did we leave off".
2. **To find how a session ENDED, phrase-match the tail**: query for wording the final message would plausibly use ("waiting on you", "your call", "merge it when ready", "what remains"). The hydrated window lands ON the last message — which is the pending question/state you need.
3. **Zoom in** with the scroll shape: `session_search(session_id=..., around_message_id=<match_message_id>, window=N)`. Keep windows small; add `role_filter="user,assistant"` to exclude tool noise.
4. **Re-fire pending prompts**: after an approval/clarify timeout, the user's "prompt me again" means re-present the SAME question — recover its text from the session tail (step 2), then re-issue it promptly. If recovery fails after one or two quick attempts, ask the user plainly what decision they're approving — never silently re-derive a different question.

## When the prior conversation is NOT in this context

A follow-up that reads as a continuation ("write a doc about this", "same branch as before") often arrives in a NEW session with none of the earlier conversation in context. Resolve the referent before acting; browse with `session_search()` (no args).

1. **Browse live activity, never infer it**: `session_search()` with no args lists the most recently ACTIVE sessions (started_at / last_active + preview). The session whose last_active is minutes old is the conversation being continued — confirm from its preview, then read or scroll it.
2. **Bound the browse with `after="<date>")`** when several sessions compete. The bound applies to session START, so a long-running session that spans days falls outside a recent bound — drop the filter for those and rank by last_active instead.
3. **Read the tail, then answer**: scroll the found session near its end (a real id from that session; the LAST id of one window re-scrolls forward) and reconstruct what the last exchange actually asked, then act on that — not on the literal wording of the new message.
4. `~/.hermes/sessions/sessions.json` is the **gateway routing index** (session key → active session id), not a session list: the key for the current thread points at the session created moments ago, while the conversation being continued sits under a different key. Use it to resolve a routing key only — never to find "the last conversation".

## Pitfalls

- **Scroll-anchor rejections are diagnostics:** "N not in session" = outside the session's id range; "anchor lives in the current session lineage" = always rejected (a fresh delivery does NOT replay it) → stop and use phrase-match (step 2); never bisect (the harness hard-stops after ~8 identical failures).
- **Keep reads narrow** (low limit, small window, `role_filter`): a whole-session read or wide scroll window spills a single-line JSON that `read_file` cannot page — switch to the DB route below before widening anything.
- **Read the session DB directly, through `sqlite3` in the terminal**: it is approval-free here and returns plain, pre-truncated rows — the cheapest way to get a session's user/assistant timeline, its tail, or a duplicate check. Recipes: `references/state-db-queries.md`.
- **Do not use `execute_code` for session recovery; use approval-free reads only** (read_file, search_files, session_search discovery/scroll, terminal `sqlite3`): approval-gated tools return BLOCKED / time out silently when the user is away and must not be retried as-is.
- **A message delivered at a session boundary is stored twice** (once in the session being continued, once in the new one): the same text appearing in two sessions is ONE user message, not a repeat. `messages.id` is global and increasing across sessions — order deliveries by id/timestamp and read the copy owned by the session that holds the current turn.
