from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from personal_os_setup.tasks.task import TaskResult


class InstallResult(BaseModel):
    """Represents the outcome of a single installation attempt.

    Attributes:
        ok: Whether the installation completed successfully.
        summary: Short, user-facing message describing the outcome.
        details: Optional diagnostic information (stdout/stderr, error context).
    """

    model_config = ConfigDict(frozen=True)

    ok: bool
    summary: str
    details: str = ""


class Installer(Protocol):
    """Protocol for a package installer backend.

    Concrete managers wrap one package manager (apt, brew, winget, etc.) and
    should be written to be as idempotent as possible.

    Note:
        This protocol is kept for backward compatibility. Prefer
        `PackageManager` for new code.
    """

    name: str

    def is_installed(self, package: str) -> bool: ...

    def install(self, package: str) -> InstallResult: ...


class PackageManager(Protocol):
    """Protocol for a system package manager backend.

    A package manager backend supports both:
        - package-level operations (`is_installed`, `install`)
        - system maintenance operations (`update`, `upgrade`, `cleanup`)

    This unifies what used to be split between an installer and a system manager
    so the UI can expose one coherent set of actions per manager.

    Attributes:
        name: A short identifier for the backend (e.g. `"apt"`).
    """

    name: str

    def is_installed(self, package: str) -> bool: ...

    def install(self, package: str) -> InstallResult: ...

    def update(self) -> TaskResult: ...

    def upgrade(self) -> TaskResult: ...

    def cleanup(self) -> TaskResult: ...
