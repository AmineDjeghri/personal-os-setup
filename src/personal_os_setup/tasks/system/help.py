from __future__ import annotations

from personal_os_setup.tasks.task import TaskResult

DOCS_SITE_URL = "https://personal-os-setup.aminedjeghri.com/docs/"


def show_documentation_link() -> TaskResult:
    """Show the published documentation site URL for copy/paste."""
    return TaskResult(
        ok=True,
        summary=DOCS_SITE_URL,
        details="Open this link in a browser to view the full documentation.",
    )
