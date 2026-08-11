from __future__ import annotations

from importlib import resources

from personal_os_setup.tasks.task import TaskResult

DOCS_SITE_URL = "https://personal-os-setup.aminedjeghri.com/docs/"


def show_documentation_link() -> TaskResult:
    """Show the published documentation site URL for copy/paste."""
    return TaskResult(
        ok=True,
        summary=DOCS_SITE_URL,
        details="Open this link in a browser to view the full documentation.",
    )


def show_packages_yaml_path() -> TaskResult:
    """Show the local path to `packages.yaml`, the catalog of installable packages."""
    path = resources.files("personal_os_setup") / "config" / "packages.yaml"
    return TaskResult(
        ok=True,
        summary=str(path),
        details="Full catalog of installable packages per distro, with descriptions as inline comments.",
    )


def show_commands() -> TaskResult:
    lines = [
        "============ Commands ============",
        "1. ls",
        "2. cat",
        "3. top",
        "4. fz or CTRL+F",
        "5. Tab, control tab etc.. for autocomplete",
        "6. folder selection with arrow when navigating",
        "7. history with arrow up",
        "8. neofetch",
    ]
    return TaskResult(ok=True, summary="commands: shown", details="\n".join(lines))
