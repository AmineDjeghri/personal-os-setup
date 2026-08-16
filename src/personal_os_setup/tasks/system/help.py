from __future__ import annotations

from personal_os_setup.tasks.task import TaskResult

DOCS_SITE_URL = "https://personal-os-setup.aminedjeghri.com/docs"


def show_documentation_link() -> TaskResult:
    """Show the published documentation site URL for copy/paste."""
    return TaskResult(
        ok=True,
        summary=DOCS_SITE_URL,
        details="Open this link in a browser to view the full documentation.",
    )


def show_apps_config_link() -> TaskResult:
    """Show the published apps configuration and shortcuts doc URL for copy/paste."""
    return TaskResult(
        ok=True,
        summary=f"{DOCS_SITE_URL}/apps/apps_configuration_and_shorcuts/",
        details="Open this link in a browser to view apps configuration and shortcuts.",
    )


def show_vm_testing_link() -> TaskResult:
    """Show the published "Testing in a VM" doc URL for copy/paste."""
    return TaskResult(
        ok=True,
        summary=f"{DOCS_SITE_URL}/linux/CachyOS/#testing-this-project-in-a-vm",
        details="Open this link in a browser to view the make vm-* VM lab docs.",
    )
