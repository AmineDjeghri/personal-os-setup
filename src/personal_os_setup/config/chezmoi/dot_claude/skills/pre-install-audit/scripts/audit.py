#!/usr/bin/env python3
"""Static pre-install audit. Fetches and reads only; never builds or executes anything.

Usage:
  audit.py aur <package>          AUR package: PKGBUILD, .install, git history, RPC metadata
  audit.py github <owner/repo>    GitHub repo: shallow clone, repo metadata, install-hook scan
  audit.py url <https://...>      A script/file (e.g. a curl|sh target): download and scan
  audit.py path <dir-or-file>     A local checkout or file

Exit code: 0 = OK, 1 = REVIEW, 2 = AVOID. Add --json for machine output.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# (severity, id, regex, message). AVOID = almost never legitimate; REVIEW = needs a human look.
RULES = [
    ("AVOID", "pipe-to-shell", r"(curl|wget|fetch)\b[^\n|;]*\|\s*(sudo\s+)?(ba|z|da|k)?sh\b", "download piped into a shell"),
    ("AVOID", "decode-exec", r"base64\s+(-d|--decode)[^\n]*\|\s*(ba|z)?sh|eval\s*\$?\(?\s*[\"']?\$\(?[^\n]*base64", "decoded payload executed"),
    ("AVOID", "reverse-shell", r"/dev/tcp/|\bnc\b[^\n]*\s-e\s|bash\s+-i\s*>&", "reverse-shell pattern"),
    ("AVOID", "raw-ip-url", r"https?://\d{1,3}(\.\d{1,3}){3}", "URL points at a raw IP"),
    ("REVIEW", "url-shortener", r"https?://(bit\.ly|tinyurl\.com|t\.co|goo\.gl|is\.gd|cutt\.ly|rb\.gy)/", "URL shortener"),
    ("REVIEW", "paste-host", r"https?://(pastebin\.com|paste\.ee|hastebin\.com|transfer\.sh|ix\.io|0x0\.st|termbin\.com)/", "paste/file-drop host"),
    ("REVIEW", "base64", r"\bbase64\b", "base64 use"),
    ("REVIEW", "eval", r"(^|[\s;&|(])eval\s", "eval"),
    ("REVIEW", "network-call", r"\b(curl|wget|nc|ncat|socat)\s", "network call (check which phase runs it)"),
    ("REVIEW", "setuid", r"chmod\s+[^\n]*(\+s\b|[ugoa]*\+s|\b[24567][0-7]{3}\b)", "setuid/setgid bit"),
    ("REVIEW", "persistence", r"(systemctl\s+(--user\s+)?enable|/systemd/(system|user)/|crontab|/etc/cron|\.config/autostart|/etc/profile\.d|\.bashrc|\.zshrc|\.profile\b|/etc/ld\.so\.preload|LD_PRELOAD)", "persistence/autostart/shell-rc hook"),
    ("REVIEW", "sensitive-paths", r"(\.ssh/|id_rsa|id_ed25519|\.gnupg|\.aws/credentials|\.config/(google-chrome|chromium|BraveSoftware)|\.mozilla/|Login Data|cookies\.sqlite|wallet\.dat|\.kube/config|\.npmrc|\.pypirc|\.netrc|\.git-credentials)", "touches credentials/browser/wallet paths"),
    ("REVIEW", "sudo", r"\bsudo\b|\bpkexec\b|\bdoas\b", "privilege escalation inside install logic"),
    ("REVIEW", "obfuscation", r"(\\x[0-9a-fA-F]{2}){8,}|[A-Za-z0-9+/]{200,}={0,2}", "long encoded/obfuscated blob"),
    ("REVIEW", "lifecycle-script", r"\"(preinstall|install|postinstall|prepare)\"\s*:", "npm lifecycle script (runs on install)"),
    ("REVIEW", "python-exec", r"\b(exec|eval)\s*\(\s*(base64|zlib|codecs|requests|urllib)|__import__\(['\"](os|subprocess)['\"]\)", "dynamic code execution in Python"),
]
COMPILED = [(s, i, re.compile(p, re.M), m) for s, i, p, m in RULES]

# Files that execute at install/build time carry the most weight.
HOOK_NAMES = {
    "PKGBUILD", ".SRCINFO", "install.sh", "setup.sh", "bootstrap.sh", "Makefile", "makefile",
    "setup.py", "setup.cfg", "pyproject.toml", "package.json", "Dockerfile", "build.rs",
    "install.ps1", "postinstall", "preinstall", "CMakeLists.txt", "meson.build",
}
HOOK_SUFFIXES = (".install", ".sh", ".ps1", ".bat", ".service", ".timer", ".desktop")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "test", "tests", "docs", "example", "examples"}
MAX_FILE = 512 * 1024


@dataclass
class Finding:
    severity: str
    rule: str
    file: str
    line: int
    text: str
    msg: str


def get(url, accept=None):
    req = urllib.request.Request(url, headers={"User-Agent": "pre-install-audit/1", **({"Accept": accept} if accept else {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(8 * 1024 * 1024)


def get_json(url):
    return json.loads(get(url))


def scan_text(name, text):
    out = []
    lines = text.splitlines()
    for sev, rid, rx, msg in COMPILED:
        for m in rx.finditer(text):
            ln = text.count("\n", 0, m.start()) + 1
            snippet = lines[ln - 1].strip()[:160] if ln - 1 < len(lines) else m.group(0)[:160]
            if snippet.lstrip().startswith("#") and rid != "pipe-to-shell":
                continue  # commented-out line
            out.append(Finding(sev, rid, name, ln, snippet, msg))
    return out


def pkgbuild_checks(name, text):
    """PKGBUILD-specific: checksum SKIP on non-VCS sources, odd source hosts."""
    out = []
    srcs = re.search(r"^source(_\w+)?=\(([^)]*)\)", text, re.M | re.S)
    sums = re.findall(r"^(?:sha\d+|md5|b2)sums(?:_\w+)?=\(([^)]*)\)", text, re.M | re.S)
    skips = sum(s.count("SKIP") for s in sums)
    vcs = bool(re.search(r"(git|svn|hg|bzr)\+|\.git\b", srcs.group(2) if srcs else ""))
    if skips and not vcs:
        out.append(Finding("REVIEW", "checksum-skip", name, 0, f"{skips}x SKIP", "checksum skipped on non-VCS source"))
    elif skips:
        out.append(Finding("REVIEW", "vcs-source", name, 0, "VCS source with SKIP", "VCS source is unpinned: content can change after review"))
    for url in re.findall(r"https?://[^\s'\")]+", srcs.group(2) if srcs else ""):
        host = urllib.parse.urlparse(url).hostname or ""
        if not re.search(r"(github\.com|gitlab\.com|codeberg\.org|sourceforge\.net|kernel\.org|gnu\.org|pypi\.org|crates\.io|npmjs\.org|archlinux\.org|files\.pythonhosted\.org|githubusercontent\.com|bitbucket\.org)$", host):
            out.append(Finding("REVIEW", "unusual-source", name, 0, url[:160], f"source host {host} is not a common forge"))
    return out


def scan_tree(root, only_hooks=False):
    findings, files = [], []
    root = Path(root)
    paths = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file() and not (set(p.relative_to(root).parts) & SKIP_DIRS))
    for p in paths:
        rel = p.name if root.is_file() else str(p.relative_to(root))
        is_hook = p.name in HOOK_NAMES or p.name.endswith(HOOK_SUFFIXES)
        if only_hooks and not is_hook:
            continue
        if p.stat().st_size > MAX_FILE:
            findings.append(Finding("REVIEW", "big-file", rel, 0, f"{p.stat().st_size} bytes", "scan skipped: file too large"))
            continue
        try:
            text = p.read_text(errors="strict")
        except (UnicodeDecodeError, OSError):
            if is_hook:
                findings.append(Finding("REVIEW", "binary-hook", rel, 0, "", "install-time file is not text"))
            continue
        files.append(rel)
        found = scan_text(rel, text)
        if p.name == "PKGBUILD":
            found += pkgbuild_checks(rel, text)
        if not is_hook:  # non-hook files only escalate on the hard rules
            found = [f for f in found if f.severity == "AVOID"]
        findings += found
    return findings, files


def age_days(ts):
    return int((time.time() - ts) / 86400)


def meta_aur(pkg):
    notes, sev = [], []
    d = get_json("https://aur.archlinux.org/rpc/v5/info?arg[]=" + urllib.parse.quote(pkg))
    if not d.get("results"):
        return ["package not found in AUR"], [Finding("AVOID", "not-found", pkg, 0, "", "no such AUR package")]
    r = d["results"][0]
    notes.append(f"maintainer={r.get('Maintainer') or 'ORPHAN'} comaint={r.get('CoMaintainers', [])}")
    notes.append(f"votes={r['NumVotes']} popularity={r['Popularity']:.2f} first_submitted={age_days(r['FirstSubmitted'])}d ago last_modified={age_days(r['LastModified'])}d ago")
    notes.append(f"upstream={r.get('URL')}  out_of_date={'yes' if r.get('OutOfDate') else 'no'}")
    if not r.get("Maintainer"):
        sev.append(Finding("REVIEW", "orphan", pkg, 0, "", "orphaned: anyone can adopt it and push changes"))
    if age_days(r["FirstSubmitted"]) < 30:
        sev.append(Finding("REVIEW", "new-package", pkg, 0, f"{age_days(r['FirstSubmitted'])}d old", "package is under 30 days old"))
    if r["NumVotes"] < 5 and r["Popularity"] < 0.1:
        sev.append(Finding("REVIEW", "low-trust", pkg, 0, f"votes={r['NumVotes']}", "few votes and low popularity"))
    return notes, sev


def history(repo, flag_authors=False):
    """Maintainer changes = the classic AUR takeover signal."""
    r = subprocess.run(["git", "-C", str(repo), "log", "--format=%an|%at|%s", "-n", "30"], capture_output=True, text=True)
    rows = [l.split("|", 2) for l in r.stdout.splitlines() if l.count("|") >= 2]
    authors = []
    for a, *_ in rows:
        if a not in authors:
            authors.append(a)
    notes = [f"{len(rows)} recent commits, authors (newest first): {', '.join(authors) or 'n/a'}"]
    sev = []
    if flag_authors and len(authors) > 1:
        sev.append(Finding("REVIEW", "multiple-authors", "git log", 0, ", ".join(authors), "history has several authors: check for a maintainer change"))
    return notes, sev


def clone(url, dest, depth=30):
    r = subprocess.run(["git", "clone", "-q", "--depth", str(depth), "--no-checkout", url, str(dest)], capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise SystemExit(f"clone failed: {r.stderr.strip()}")
    # no hooks, no submodules, no LFS smudge: plain checkout only
    subprocess.run(["git", "-C", str(dest), "-c", "core.hooksPath=/dev/null", "-c", "filter.lfs.smudge=", "checkout", "-q"], check=True, capture_output=True)


def audit_aur(pkg, tmp):
    notes, sev = meta_aur(pkg)
    if any(f.rule == "not-found" for f in sev):
        return notes, sev, []
    repo = Path(tmp) / pkg
    clone(f"https://aur.archlinux.org/{urllib.parse.quote(pkg)}.git", repo)
    n2, s2 = history(repo, flag_authors=True)
    findings, files = scan_tree(repo)
    return notes + n2, sev + s2 + findings, files


def audit_github(slug, tmp):
    notes, sev = [], []
    try:
        r = get_json(f"https://api.github.com/repos/{slug}")
        u = get_json(r["owner"]["url"])
        notes.append(f"stars={r['stargazers_count']} forks={r['forks_count']} created={age_days(time.mktime(time.strptime(r['created_at'], '%Y-%m-%dT%H:%M:%SZ')))}d ago pushed={age_days(time.mktime(time.strptime(r['pushed_at'], '%Y-%m-%dT%H:%M:%SZ')))}d ago")
        notes.append(f"owner={u['login']} ({u['type']}) account_age={age_days(time.mktime(time.strptime(u['created_at'], '%Y-%m-%dT%H:%M:%SZ')))}d public_repos={u['public_repos']}")
        notes.append(f"archived={r['archived']} fork={r['fork']} license={(r.get('license') or {}).get('spdx_id')} default_branch={r['default_branch']}")
        if r["fork"]:
            sev.append(Finding("REVIEW", "is-fork", slug, 0, r.get("parent", {}).get("full_name", "") if "parent" in r else "", "fork: compare against the original, forks are a common impersonation vector"))
        if r["stargazers_count"] < 10:
            sev.append(Finding("REVIEW", "low-stars", slug, 0, str(r["stargazers_count"]), "very few stars"))
        if age_days(time.mktime(time.strptime(r["created_at"], "%Y-%m-%dT%H:%M:%SZ"))) < 30:
            sev.append(Finding("REVIEW", "new-repo", slug, 0, "", "repo is under 30 days old"))
    except Exception as e:  # rate limit etc.: metadata is advisory, scan still runs
        notes.append(f"github metadata unavailable: {e}")
    repo = Path(tmp) / slug.replace("/", "_")
    clone(f"https://github.com/{slug}.git", repo)
    n2, s2 = history(repo)
    findings, files = scan_tree(repo, only_hooks=True)
    return notes + n2, sev + s2 + findings, files


def audit_url(url, tmp):
    data = get(url)
    p = Path(tmp) / (Path(urllib.parse.urlparse(url).path).name or "download")
    p.write_bytes(data)
    notes = [f"{len(data)} bytes from {urllib.parse.urlparse(url).hostname}; sha256 below, pin it if you run it"]
    import hashlib
    notes.append("sha256=" + hashlib.sha256(data).hexdigest())
    sev = []
    if url.startswith("http://"):
        sev.append(Finding("AVOID", "plain-http", url, 0, "", "downloaded over plain HTTP: tamperable in transit"))
    findings, files = scan_tree(p)
    return notes, sev + findings, files


def collapse(findings):
    """One line per (rule, file): keep the first hit, count the rest."""
    first, extra, out = {}, {}, []
    for f in findings:
        k = (f.rule, f.file)
        if k in first:
            extra[k] = extra.get(k, 0) + 1
        else:
            first[k] = f
            out.append(f)
    for k, n in extra.items():
        first[k].msg += f" (+{n} more)"
    return out


def verdict(findings):
    if any(f.severity == "AVOID" for f in findings):
        return "AVOID"
    return "REVIEW" if findings else "OK"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["aur", "github", "url", "path"])
    ap.add_argument("target")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.kind in ("aur", "github") and not shutil.which("git"):
        sys.exit("git is required")
    tmp = tempfile.mkdtemp(prefix="pre-install-audit-")
    try:
        if a.kind == "aur":
            notes, findings, files = audit_aur(a.target, tmp)
        elif a.kind == "github":
            notes, findings, files = audit_github(a.target.removeprefix("https://github.com/").removesuffix(".git").strip("/"), tmp)
        elif a.kind == "url":
            notes, findings, files = audit_url(a.target, tmp)
        else:
            notes = []
            findings, files = scan_tree(a.target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    findings = collapse(findings)
    v = verdict(findings)
    if a.json:
        print(json.dumps({"verdict": v, "notes": notes, "files": files, "findings": [f.__dict__ for f in findings]}, indent=2))
    else:
        print(f"VERDICT: {v}")
        for n in notes:
            print("  " + n)
        print(f"  scanned: {', '.join(files) or 'nothing'}")
        for f in sorted(findings, key=lambda f: (f.severity != "AVOID", f.file, f.line)):
            loc = f"{f.file}:{f.line}" if f.line else f.file
            print(f"  [{f.severity}] {f.rule} {loc}: {f.msg}" + (f"\n      {f.text}" if f.text else ""))
    sys.exit({"OK": 0, "REVIEW": 1, "AVOID": 2}[v])


if __name__ == "__main__":
    main()
