# SSH & TLS/SSL fundamentals

<!-- TOC -->
* [SSH & TLS/SSL fundamentals](#ssh--tlsssl-fundamentals)
  * [Why bother understanding this](#why-bother-understanding-this)
  * [SSH: two separate trust directions](#ssh-two-separate-trust-directions)
    * [1. Client verifies the server (known_hosts)](#1-client-verifies-the-server-known_hosts)
    * [2. Server verifies the client (authorized_keys)](#2-server-verifies-the-client-authorized_keys)
    * [What's actually happening underneath (key exchange)](#whats-actually-happening-underneath-key-exchange)
    * [Session multiplexing](#session-multiplexing)
  * [TLS/SSL: trust at internet scale](#tlsssl-trust-at-internet-scale)
    * [The problem TLS solves that SSH doesn't](#the-problem-tls-solves-that-ssh-doesnt)
    * [How a TLS certificate is verified](#how-a-tls-certificate-is-verified)
    * [Mutual TLS (mTLS) — TLS's version of authorized_keys](#mutual-tls-mtls--tlss-version-of-authorized_keys)
    * [Why corporate laptops have their own CA (TLS interception)](#why-corporate-laptops-have-their-own-ca-tls-interception)
  * [SSH vs TLS — side by side](#ssh-vs-tls--side-by-side)
  * [Applying this to the home server](#applying-this-to-the-home-server)
    * [SSH into the server](#ssh-into-the-server)
    * [TLS for anything exposed via Cloudflare Tunnel / a reverse proxy](#tls-for-anything-exposed-via-cloudflare-tunnel--a-reverse-proxy)
    * [Self-signed certs on the LAN](#self-signed-certs-on-the-lan)
  * [Common errors and what they actually mean](#common-errors-and-what-they-actually-mean)
<!-- TOC -->

## Why bother understanding this

Both SSH and TLS solve the same underlying problem — "how do two computers that have never met agree to trust each other, and encrypt what they say?" — but they solve it differently, and mixing up the mental models is where most confusion (and misconfiguration) comes from. This doc lays out both, side by side, so config choices on the home server (SSH hardening, Cloudflare Tunnel, any local HTTPS service) make sense instead of being cargo-culted.

## SSH: two separate trust directions

SSH does **two independent checks**, in opposite directions. It's easy to only think about one of them.

### 1. Client verifies the server (known_hosts)

The first time you `ssh` into a new host, you get a prompt like:

```
The authenticity of host 'homeserver (192.168.1.50)' can't be established.
ED25519 key fingerprint is SHA256:xxxxx.
Are you sure you want to continue connecting (yes/no)?
```

The server has a keypair of its own (usually generated once, at `/etc/ssh/ssh_host_ed25519_key` etc.). It proves it holds the private key; your client checks the matching public key against `~/.ssh/known_hosts`. This is **trust on first use (TOFU)** — you manually vouch for the server the first time, and every future connection is checked against that pinned fingerprint. If the fingerprint ever changes unexpectedly, SSH refuses to connect and warns loudly — that's what catches a man-in-the-middle or a wiped/reinstalled host.

**The `known_hosts` line format:**

```
<host> <key-type> <base64-public-key> [comment]
```

- `<host>` — hostname or IP (or `hostname,ip` for both). If `HashKnownHosts yes` is set, this is instead an opaque `|1|salt|hash` string rather than plaintext — a privacy option so a leaked file doesn't reveal which hosts you connect to.
- `<key-type>` — the algorithm: `ssh-ed25519`, `ssh-rsa`, `ecdsa-sha2-nistp256`, etc.
- `<base64-public-key>` — the server's actual public key bytes, not a hash of it.

It's normal to see the *same host* on several lines, one per algorithm — a server generates one host keypair per algorithm it supports, and your client records whichever ones it has actually negotiated over time.

**What happens during the handshake, step by step:**

1. Client and server negotiate a key-exchange algorithm and start a Diffie-Hellman exchange (see [key exchange](#whats-actually-happening-underneath-key-exchange) below).
2. As part of that exchange, the server signs the handshake data with its host *private* key and sends the signature plus its public key.
3. The client verifies the signature against the public key just presented — proving the server holds the private key matching whatever public key it's claiming (self-consistency check, doesn't touch `known_hosts` yet).
4. The client looks up `<host>` in `known_hosts` for a matching key type, and compares the presented public key **byte-for-byte** against the stored one.
5. Match → connection proceeds silently, no prompt. This all happens before you type a password or your own key is challenged.

**Why "unknown" and "changed" are handled so differently:** if the host isn't in `known_hosts` at all, you get the "authenticity can't be established" prompt, and answering yes appends a new line. But if the host *is* present and the key bytes don't match what's stored, SSH doesn't prompt — it refuses outright with a loud `REMOTE HOST IDENTIFICATION HAS CHANGED!` warning and exits. This asymmetry is deliberate: if a changed key only triggered the same "are you sure?" prompt people click through by habit, a man-in-the-middle could simply substitute their own key and rely on users clicking yes anyway.

### 2. Server verifies the client (authorized_keys)

This is the direction most people think of as "SSH keys": you generate a keypair (`ssh-keygen -t ed25519`), keep the private key secret on your laptop, and put the **public** key in `~/.ssh/authorized_keys` on the server. On login, the server challenges your client to sign some random data with the private key — proving you hold it, without the private key ever leaving your machine.

These two checks are independent and happen in opposite directions — the server never needs your public key to prove *its own* identity, and you never need to trust the server's key to *authenticate yourself* to it.

### What's actually happening underneath (key exchange)

Before either trust check completes, SSH does a **Diffie-Hellman key exchange**: client and server use math to agree on a shared symmetric session key, without ever transmitting that key over the wire. Public-key crypto (RSA/Ed25519) is comparatively slow, so it's only used briefly during this handshake — the actual data of your session (commands, file transfers) is encrypted with the fast symmetric key it produced. Host key verification and authentication both happen *after* this, i.e. already inside an encrypted tunnel.

### Session multiplexing

Once authenticated, a single SSH connection can carry multiple logical "channels" — your interactive shell, but also `scp`/`sftp` transfers, port forwards (`-L`/`-R`, handy for reaching services on the home server without exposing them publicly), and X11 forwarding, all inside the one encrypted connection.

## TLS/SSL: trust at internet scale

### The problem TLS solves that SSH doesn't

SSH's TOFU model works because you personally manage a short list of servers you connect to. TLS was designed for browsers connecting to millions of websites they've never seen, with zero manual setup per site. That requires delegating trust to third parties instead of pinning it yourself.

### How a TLS certificate is verified

1. A server has a private key and a **certificate**: its public key + identity ("I am `example.com`"), digitally signed by a **Certificate Authority (CA)**.
2. On connecting, the server sends this certificate.
3. Your OS/browser ships with a **trust store** — the public keys of ~100+ root CAs it already trusts (Let's Encrypt, DigiCert, etc.).
4. If the certificate's signature chains back to something in that trust store, the connection proceeds silently. If not: `CERTIFICATE_VERIFY_FAILED`.

This is the same *shape* of problem as SSH's known_hosts (client verifying server identity), just automated via a hierarchy of signers instead of manual fingerprint-pinning.

One subtlety worth knowing: **different programs on the same machine can keep separate trust stores**. macOS/Windows have a system-level keychain that browsers and `curl` typically use; but many language runtimes (Python's `ssl`/`urllib`, sometimes Node's `https`) ship or reference their *own* separate CA bundle file, independent of the OS keychain. Installing a CA into "the system" doesn't always mean every tool on that machine will trust it — this is exactly what causes the corporate-proxy cert error covered in the [Common errors](#common-errors-and-what-they-actually-mean) section below, and it can bite in a homelab context too (e.g. running your own internal CA for LAN services, but only importing it into the browser and not into `curl`/Python/Docker's trust store).

### Mutual TLS (mTLS) — TLS's version of authorized_keys

By default TLS only does the SSH-known_hosts-equivalent direction: client verifies server. Browsers never "register" a key with a website first. But TLS *can* do the other direction too — **mutual TLS (mTLS)**: the server also demands and verifies a client certificate. This is the direct analogue of SSH's `authorized_keys` step, and it's how a lot of service-to-service auth works (it's conceptually similar to how AWS SigV4-signed requests authenticate a caller, too). Cloudflare Tunnel's `cloudflared` client authenticating to Cloudflare's edge is effectively this pattern.

### Why corporate laptops have their own CA (TLS interception)

TLS's entire design goal is "nobody in the middle can read or tamper with this, not even the network it travels over." A company's security team, however, often *wants* to see inside that traffic — scanning downloads for malware, blocking data exfiltration, enforcing content policy, logging for compliance. TLS was built specifically to prevent exactly this kind of interception by an untrusted third party. So a company that wants it anyway has only one option: stop being an untrusted third party, by making itself a **trusted** one.

**How that actually works, mechanically:**

1. IT generates its own private root CA (a keypair, just like any CA — it's not fundamentally different from a public one, just never handed to a public trust program).
2. That CA's *public* half gets pushed to every managed device via MDM, into the OS-level trust store — the same one holding DigiCert, Let's Encrypt, etc.
3. All outbound traffic is routed through a **forward proxy** (via system network settings, a PAC file, or a client agent). This is a real, physical man-in-the-middle — deliberately.
4. When you visit `https://example.com`, the proxy intercepts the connection before it reaches the real internet. It opens its *own* separate TLS connection to the real `example.com` (verifying the real certificate itself, on your behalf), and separately, it generates a **fresh certificate for `example.com` on the fly**, signed by the company's own CA — not the site's real one — and hands that to you.
5. Your browser checks that certificate's signature chain: does it lead back to something in the trust store? Yes — because step 2 planted the company's CA there. No warning, padlock shows normally.
6. The proxy now sits in the middle with two separate decrypted TLS sessions (you↔proxy, proxy↔real site), and can read, log, or block anything passing through in plaintext, before re-encrypting each direction.

This category of product is usually called **TLS/SSL inspection** or a **secure web gateway** (well-known commercial examples include Zscaler, Netskope, Palo Alto, and similar — any given company's MDM CA cert is typically visible in macOS Keychain Access under a name like `<Company> Proxy CA` if you go looking).

**Two otherwise-identical MacBooks, side by side:**

| | Personal Mac | Corporate Mac |
|---|---|---|
| Trust store | Only public CAs (Apple's default bundle) | Public CAs **+** the company's own root CA |
| Route to the internet | Direct | Through the company's forward proxy |
| Certificate you actually receive for `example.com` | The real one, signed by a public CA | A substitute, signed by the company's CA, for the *same* domain |
| Who can read your HTTPS traffic in plaintext | Nobody in transit | The proxy, for anything routed through it |

**Why some sites fail only on the corporate machine — two different causes:**

- **Certificate pinning.** Some apps and services don't trust "whatever's in the OS trust store" — they hardcode ("pin") the exact certificate or CA they expect, specifically as a defense *against* this kind of interception. Banking apps, some enterprise SaaS, and certain package registries do this. When pinning is present, the proxy's substitute certificate is rejected outright, no matter what's installed in your trust store — this is the one case TLS inspection categorically cannot work around, by design.
- **Separate trust stores per tool**, the same issue covered earlier in this doc: MDM only installs the company CA into the *OS-level* store. Tools that ship or reference their own CA bundle instead of consulting the OS store (Python's `urllib`/`ssl`, sometimes Docker, older Java runtimes) never see that CA and fail with the exact `CERTIFICATE_VERIFY_FAILED: self-signed certificate` error, even though Safari/Chrome — reading the same request against the same site, on the same machine — work fine.

**The consequence worth being deliberate about:** any personal account you use on a corporate, MDM-managed machine (personal email, banking, messaging) has its HTTPS traffic technically decryptable by whatever's running on that proxy, for the duration it's routed through it — policy may restrict what's actually logged or inspected, but the technical capability exists at the network layer regardless of policy. It's generally worth keeping fully personal browsing on a personal device instead.

## SSH vs TLS — side by side

| | SSH | TLS/SSL |
|---|---|---|
| Client verifies server | `known_hosts`, manual TOFU pinning | CA-signed certificate chain, trust store |
| Server verifies client | `authorized_keys` (public key you placed there) | Optional — mutual TLS (mTLS), rarely used by default |
| Session encryption | Diffie-Hellman → symmetric session key | Same handshake pattern (TLS handshake → symmetric session key) |
| Trust model | You decide who to trust, per-host | Delegated to third-party CAs, scales to millions of unknown servers |
| Typical failure mode | "Host key verification failed" (fingerprint changed) | "Certificate verify failed" (signer not in trust store) |

## Applying this to the home server

### SSH into the server

- The server's host key lives under `/etc/ssh/ssh_host_*_key` — back it up if you ever reinstall the OS but want to keep the same fingerprint (otherwise every client that already has it in `known_hosts` will refuse to connect until you manually remove the stale entry).
- Prefer key-based auth (`authorized_keys`) over password auth; disable password auth entirely in `/etc/ssh/sshd_config` (`PasswordAuthentication no`) once your key is confirmed working, to remove brute-force risk if the server is ever reachable from outside the LAN.
- If exposing SSH outside the LAN (not recommended without a good reason), consider putting it behind the same Cloudflare Tunnel used for Home Assistant rather than port-forwarding it directly on the router.

### TLS for anything exposed via Cloudflare Tunnel / a reverse proxy

- Cloudflare Tunnel terminates TLS at Cloudflare's edge using a certificate Cloudflare manages — you don't need to run your own cert for the public hostname. This is why it "just works" from a browser with a padlock and no warnings.
- If you add your own reverse proxy in front of a service (nginx/Caddy/Traefik) for internal access instead of going through the tunnel, that's where you'd manage your own cert — Let's Encrypt via ACME is the standard free option for anything with a real public DNS name.

### Self-signed certs on the LAN

- For services only reached over the local network (e.g. `https://homeserver.local`), a public CA can't issue you a cert (no public DNS validation possible), so the common options are: a self-signed cert (browser will warn every time unless you import it into each device's trust store — same "which trust store" issue mentioned above), or running your own tiny local CA (e.g. `mkcert` or `step-ca`) and importing *that* CA's root into each device once — after which every cert it issues is trusted silently, no more warnings.

## Common errors and what they actually mean

- **`Host key verification failed`** (SSH) — the server's fingerprint doesn't match what's in your `known_hosts`. Either the server was reinstalled/its key regenerated (expected, just remove the old entry with `ssh-keygen -R <host>`), or — rarely — something is intercepting the connection. Don't blindly remove-and-reconnect on a network you don't fully trust without checking why it changed.
- **`CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain`** (TLS) — the certificate's signer isn't in the trust store the connecting program is using. On a corporate laptop this is usually a TLS-inspecting proxy whose CA is trusted by the OS/browser but not by whatever CA bundle the failing tool reads (Python's `urllib`/`ssl` module is a common offender, since it doesn't consult the OS keychain the way `curl` does). Fix: get the relevant CA cert(s) into the trust store the failing tool actually consults (e.g. Python's `SSL_CERT_FILE` env var), not just the OS-level one.
- **`certificate has expired`** — self-explanatory, but note Let's Encrypt certs are short-lived (90 days) by design to force automation (`certbot`/ACME renewal) rather than manual, error-prone renewal.
