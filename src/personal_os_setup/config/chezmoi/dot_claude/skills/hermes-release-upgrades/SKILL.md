---
name: hermes-release-upgrades
description: "Use when Hermes was just upgraded or a new release is checked out."
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [hermes, upgrade, release, verification, features, testing]
    related_skills: [hermes-instance-audit, skill-deployment, hermes-cron-automations]
---

# Verifying a new Hermes release on this box

The user upgrades Hermes often and then asks "what can we use from this release / test it".
This skill is the procedure and the accumulated per-feature evidence. Feature inventory lives in
the release notes; this file holds what this box actually proved.

## 1. First: is the new code even running?

`hermes update` swaps the checkout. It does **not** restart the gateway or the dashboard, so the
process serving this chat keeps executing the OLD code, and every "test" run against the CLI can
still hit a stale long-running service.

```bash
hermes --version                  # tag + build sha — proves the checkout, not the running process
hermes status | head -3           # banner "manual restart still pending" = stale owner, restart it
ps -o pid,lstart,etime -p $(pgrep -f "hermes gateway run" | head -1)
```

Compare the gateway start time with the install time (`stat -c %y <install>/pyproject.toml`). A
gateway started **before** the update answers with pre-update behaviour: CLI subcommands read the
new code (they are fresh processes), the gateway-side features (session authority, cron tick,
adapters, plugin runtime) do not.

- Report this as a blocker with the two timestamps, ask for a restart, and label anything already
  tested as "CLI-side only".
- After the restart, re-run the gateway-side probes; don't carry over a conclusion from the stale pass.

## 2. Test on disposable artifacts, never on live state

Scratch skill under `~/.hermes/skills/hermes-testing/` (delete after), scratch cron job with
`--deliver local` and a `sleep` body, throwaway session for `refresh-prompts`. Never edit one of his
authored skills, a live cron job, or `config.yaml` to prove a feature.

Cleanup is part of the test: a scratch cron job left `running` blocks that job forever (see §4).

## 3. Probe recipes (fast, read-only, no LLM cost)

```bash
hermes plugins check-updates                    # read-only, table + "Check-only" footer
hermes plugins auto-update                      # prints current plugins.auto_apply state
hermes webapp --status                          # "The Webapp is off. Set webapp.enabled…"
hermes sessions refresh-prompts --session <id> --json   # {"epoch":1,"sessions":1}
hermes curator status | tail -15                # per-skill usage telemetry (use/view/patches)
for k in webapp.enabled compression.prepare_ahead agent.stream_max_lifetime \
         plugins.auto_apply delegation.backend vault.key_storage cron.catch_up_missed; do
  printf '%-32s = %s\n' "$k" "$(hermes config get $k 2>&1 | tail -1)"
done
```

`hermes plugins search <term> --json` is the reliable catalog query — the human table truncates
columns and the ranking puts unrelated entries first, so never judge a search by its first row.
`hermes plugins show <name>` only resolves **installed** plugins.

## 4. Findings that contradict the release notes (keep this list current)

- **`hermes curator lock` is one-way for the agent.** It blocks `skill_manage`, `write_file`,
  `patch` **and** `terminal` — and `hermes curator unlock` is itself refused ("Only the user can
  unlock a skill"). So a locked skill also blocks the deploy pipeline (`make skills-…-to-live`
  runs as the agent). Test lock on a scratch skill and ask the user to run the `unlock` themselves.
- **`hermes cron cancel` does not cover a manual `hermes cron run`.** The scheduler-dispatched run
  is cancellable; a run started by `cron run` is booked `source=direct`, the CLI answers "Nothing
  to cancel", the row stays `running` after the script exits, and the job stops firing on schedule
  (the next tick is skipped because the run looks in flight). Fix = `hermes cron remove <id>`.
  Prove the state with `hermes cron runs <id>` before and after.
- **`hermes cron run` blocks the calling shell** until the run finishes — never call it foreground
  with a long job; it eats the whole `terminal` timeout.
- **The Webapp bundle does build in the agent container** (`hermes webapp --build-only`, a few minutes,
  no flags needed) → `~/.hermes/hermes-agent/apps/desktop/dist-webapp`. So enabling it is only
  `webapp.enabled: true` + a gateway restart; build failures are not the reason to skip it. Run it in the
  background and keep testing other things.

## 5. What only the user can test

Hand these over as a short numbered list with the exact action, and say what a pass looks like:

| Feature | Surface | Pass looks like |
|---|---|---|
| `/rewind` (Esc Esc) | TUI / classic CLI | earlier message editable, fork offered, original session unchanged |
| Inline terminal images | TUI (kitty/Ghostty), CLI (iTerm2/WezTerm/Konsole) | screenshot drawn, not a path |
| Telegram: video note, `dm_topic_auto_transfer`, silent unaddressed group messages | phone | note reaches the agent; new topic per root-DM message |
| Webapp | browser on LAN | `webapp.enabled: true` + gateway restart, sign-in link from `hermes webapp --no-open` |
| Price tags / spend limits | any approval prompt | price + running total shown |
| `/usage` allowance bars, `/model reset` | any chat | bars with reset time; session back on default model |

## 6. Reporting back

Split the report: **verified here** (command + observed output), **yours to test** (the table above),
**defects** (with the repro). Then write the durable part — the commands that worked and the
contradictions — into this skill; the release notes go stale, this file is the memory. Don't paste
the changelog back to him.

Only after the findings are recorded: deploy edited skills (`skill-deployment`), and tell any
already-running session to pick them up with `hermes sessions refresh-prompts`.
