# Claude Code OAuth device flow — verified transcript (Aug 2026)

Working flow on the Hermes HA addon (Claude Code 2.1.248, native install, HOME=/config).

## The wrong path (do not repeat)

First-run interactive `claude` in a background PTY showed the setup screen:

```
Welcome to Claude Code v2.1.248 ... Let's get started.
Choose the text style that looks best with your terminal
1. Auto (match terminal)    ❯2. Darkmode ✔    3. Lightmode ...
```

Multiple `process(action="submit")` (Enter) presses did **not** advance the picker
(output stayed on the same frame; only stray control bytes appended). **Do not fight it.**
Kill the session (`process action="kill"`) and use the subcommand below.

## The working path

1. Start: `terminal(command="/config/.local/bin/claude auth login", background=true, pty=true)`.
2. Poll (`process action="wait"` / `"poll"`). Expected output:

```
Opening browser to sign in…
If the browser didn't open, visit: https://claude.com/cai/oauth/authorize?code=true&client_id=...&code_challenge=...&state=<STATE>
Paste code here if prompted >
```

3. Hand the user the full URL in a `text` code block (it is a one-time PKCE URL —
   expires; a fresh `claude auth login` mints a new one). They open it on their phone
   in a browser logged into their claude.ai account (Pro/Max subscription).
4. The user pastes the code back into chat. The code arrives as a single line WITH a
   `#state` suffix, e.g.:

```
nRMp4KqO1lPYQOuZ6ZeSe0BhwVYXEwpGVhQqgRkA9lqqWe9v#p9xECarUYQ3BWwGsFXU10Wzws5FVnossYbJyHr_jOH0
```

   Submit the ENTIRE string, suffix included: `process(action="submit", data="<full code>")`.
5. Poll: expect `Login successful.` and process exit 0.
6. Verify: `/config/.local/bin/claude auth status` → `loggedIn: true`,
   `authMethod: "claude.ai"`, `subscriptionType: "pro"`.

## Gotchas

- The `#state` suffix is part of the code — stripping it breaks the exchange.
- The device-flow URL contains query params (`client_id`, `code_challenge`, `state`):
  it is one-shot. Re-run `claude auth login` for a fresh pair if it lapses.
- Auth state persists under /config (HOME=/config), so login survives addon updates.
- If the install approval gate times out, the user may install manually — verify
  (`--version`, `doctor`, `auth status`) instead of re-running the installer.
