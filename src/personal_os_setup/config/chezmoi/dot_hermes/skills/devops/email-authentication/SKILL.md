---
name: email-authentication
description: Use when auditing or hardening email auth for a domain.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [dns, email, spf, dkim, dmarc, bimi, spoofing, deliverability, cloudflare]
    related_skills: [home-assistant-network-diagnostics]
---

# Email authentication (SPF / DKIM / DMARC / BIMI)

Audit and harden a domain's email authentication so the domain cannot be spoofed, and read a
provider's "email security" scorecard (Cloudflare Email Security, registrar/host warnings) without
guessing. Probes are read-only and need no API token; every fix is a DNS record or a toggle in the
mail provider's own panel.

## When to use
- "What is this: Block fake emails sent from my domain?" · "is my domain spoofable?"
- "Why do my mails land in spam?" · "do I still need SPF / DKIM / DMARC?"
- After a registrar, host or Cloudflare shows an email-security warning and the user wants to know
  whether to act
- Before/after publishing a mail-auth record (verification)

## What each record actually does
| Record | Meaning | Notes |
|---|---|---|
| `TXT @` (SPF) | which servers may send for the domain | `~all` = softfail (mark), `-all` = hardfail (reject). One SPF record per name. |
| `TXT <selector>._domainkey` (DKIM) | cryptographic signature on outgoing mail | **the selector is chosen by the mail provider** — never hand-write keys, take the name from the panel; absence under guessed selectors is not proof |
| `TXT _dmarc` (DMARC) | what receivers do when SPF/DKIM FAIL, plus where to send reports | `p=none` = monitor only; `rua=` = aggregate reports |
| `TXT default._bimi` (BIMI) | brand logo in the inbox | NOT anti-spoofing: needs enforced DMARC + a paid VMC certificate → cosmetic, skip unless asked |

## Procedure (the order is the whole point)
1. **Probe the current state first** (recipe below), read-only — a scorecard can render `p=none` as
   "None" and read like "no DMARC record" when one exists.
2. **Fix DKIM before anything strict** — enable it in the mail provider's panel (e.g. Hostinger
   hPanel → Emails → DNS/DKIM), which publishes the selector record itself. Without a signature a
   strict DMARC policy is unsafe and the reports say nothing useful.
3. **Publish DMARC at `p=none`** with the reporting address the provider offers (Cloudflare's
   one-click writes `v=DMARC1; p=none; rua=mailto:<hash>@dmarc-reports.cloudflare.net`). Zero
   delivery impact; it only starts collecting.
4. **Wait ~1-2 weeks, then read the reports** ("third parties sending emails on your behalf"). Only
   if every legitimate sender passes do you escalate.
5. **Escalate one step at a time:** `p=none` → `p=quarantine` → `p=reject`. Tighten SPF `~all` →
   `-all` only after enforcement, and only once no other service sends with that From.
6. **Verify end-to-end**: send a test mail to a Gmail account and read "Show original" — you want
   `SPF: PASS`, `DKIM: PASS`, `DMARC: PASS` on the same message. A record existing in DNS is not
   proof that legitimate mail aligns.

## Read-only probe recipe (public DoH, no token/API)
```bash
q(){ curl -s -m 10 "https://dns.google/resolve?name=$1&type=$2" | tr ',' '\n' | grep -E '"data"|"Status"' | tr '\n' ' '; echo; }
q <domain> MX            # who receives -> names the mail host
q <domain> TXT           # SPF
q _dmarc.<domain> TXT    # DMARC (Status:3 = NXDOMAIN = absent)
q <candidate-selector>._domainkey.<domain> TXT   # DKIM
q random-test-<n>.<domain> A                     # CONTROL: NXDOMAIN proves no wildcard
```
- `Status:0` + `data` = present, `Status:3` = NXDOMAIN (absent).
- Enumerate 4-6 plausible DKIM selectors (`default`, `dkim`, `mail`, provider-prefixed ones) — but
  state plainly that a real selector may exist under a name you did not guess.
- No mail-auth tooling needed; the DoH endpoint answers from any container with egress.

## Pitfalls
- **Never recommend `p=reject` while DKIM is absent** — SPF-only alignment breaks as soon as mail
  travels through a forwarder or a second sending path, and reject bins those messages silently.
- "SPF softfail" on a scorecard = `~all`; "hardfail" = `-all`. Tightening SPF before DMARC
  enforcement buys almost nothing — fix the order, not the strength.
- A warning about a missing record is not proof the domain's mail is broken: check MX and the mail
  provider's own logs before touching auth records. Delivery complaints are usually not auth.
- Say the price out loud when the user asks about BIMI (VMC ≈ yearly fee) instead of listing it as
  a to-do next to free fixes.
- Mail-auth records live in the same zone as the public DNS records, so a wildcard record there is
  also what makes a retired hostname keep answering — run the random-subdomain control in both tasks.
