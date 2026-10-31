"""Fail incomplete integration runs and record a concise, credential-free result.

Failure rule (deliberate, do not "fix" it back to the strict template version): each OS job
skips the other platforms' modules by design, so skipped tests are NOT a failure here. The run
fails when ANY of these holds:

* zero tests passed (e.g. a runner-label change or a ``-k``/``-m`` filter left nothing to run);
* any integration case was deselected, or the run only collected tests;
* a test failed.

Enabled by ``make test-integration``. Diagnostic collection cannot pass this validation gate.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from _pytest.terminal import TerminalReporter

RULE = (
    "Rule: skipped tests are expected (each OS job skips the other platforms' modules); the run "
    "fails when zero tests passed, integration cases were deselected, the run only collected "
    "tests, or a test failed."
)


@dataclass(eq=False)
class IntegrationResults:
    """Track execution on the controller, including reports from xdist workers."""

    passed: set[str] = field(default_factory=set)
    failed: set[str] = field(default_factory=set)
    skipped: set[str] = field(default_factory=set)
    deselected: set[str] = field(default_factory=set)

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Record each report; a failing teardown counts as a failure, a skip never does."""
        if report.skipped:
            self.skipped.add(report.nodeid)
        elif report.failed:
            self.failed.add(report.nodeid)
        elif report.when == "call":
            self.passed.add(report.nodeid)

    def pytest_deselected(self, items: list[pytest.Item]) -> None:
        """Detect filters that omit integration cases while ignoring ordinary unit cases."""
        for item in items:
            if item.get_closest_marker("integration") or "/integration/" in item.nodeid:
                self.deselected.add(item.nodeid)

    @pytest.hookimpl(optionalhook=True)
    def pytest_testnodedown(self, node: Any, error: object) -> None:
        """Merge worker selection results so filtered parallel runs cannot pass as complete."""
        self.deselected.update(getattr(node, "workeroutput", {}).get("integration_deselected", []))

    def failure_reasons(self, collect_only: bool = False) -> list[str]:
        """Return why execution is incomplete while allowing expected platform skips."""
        reasons = []
        if collect_only:
            reasons.append("collection-only run")
        if self.failed:
            reasons.append(f"{len(self.failed)} test(s) failed")
        if self.deselected:
            reasons.append(f"{len(self.deselected)} integration test(s) deselected")
        if not self.passed:
            reasons.append("zero integration tests passed")
        return reasons

    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:
        """Require at least one executed passing test and publish counts without test payloads."""
        if hasattr(session.config, "workerinput"):
            worker_output = getattr(session.config, "workeroutput", None)
            if isinstance(worker_output, dict):
                worker_output["integration_deselected"] = sorted(self.deselected)
            return
        reasons = self.failure_reasons(session.config.option.collectonly)
        complete = not (reasons or exitstatus)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with Path(summary).open("a") as stream:
                stream.write(
                    f"\nIntegration validation: **{'complete' if complete else 'incomplete'}**. "
                    f"Passed: {len(self.passed)}; failed: {len(self.failed)}; "
                    f"skipped: {len(self.skipped)}; deselected: {len(self.deselected)}.\n"
                )
                if reasons:
                    stream.write(f"Incomplete because: {'; '.join(reasons)}. {RULE}\n")
        # Give empty/all-skipped runs the same failing status as a failed integration case.
        if reasons and exitstatus in (pytest.ExitCode.OK, pytest.ExitCode.NO_TESTS_COLLECTED):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED

    def pytest_terminal_summary(self, terminalreporter: TerminalReporter) -> None:
        """Make zero-execution failures visible in local and CI output."""
        reasons = self.failure_reasons(terminalreporter.config.option.collectonly)
        terminalreporter.write_sep(
            "=",
            "Integration execution: "
            f"{len(self.passed)} passed, {len(self.failed)} failed, "
            f"{len(self.skipped)} skipped, {len(self.deselected)} deselected."
            + (f" INCOMPLETE: {'; '.join(reasons)}. {RULE}" if reasons else ""),
            red=bool(reasons),
        )


def pytest_configure(config: pytest.Config) -> None:
    """Enable strict integration reporting only when this plugin is explicitly selected."""
    config.pluginmanager.register(IntegrationResults(), "integration-results")
