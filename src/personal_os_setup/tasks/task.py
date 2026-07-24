from __future__ import annotations

from typing import Callable, Iterable

from pydantic import BaseModel, ConfigDict

from personal_os_setup.settings import logger


class TaskResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    summary: str
    details: str = ""


class Task(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    requires_admin: bool
    check: Callable[[], bool]
    run: Callable[[], TaskResult]


def run_tasks(tasks: Iterable[Task]) -> list[TaskResult]:
    results: list[TaskResult] = []
    for t in tasks:
        logger.info(f"==> {t.title}")
        try:
            if t.check():
                logger.info("Already applied. Skipping.")
                results.append(TaskResult(ok=True, summary=f"{t.title}: already applied"))
                continue
            res = t.run()
            results.append(res)
            logger.info(res.summary)
            if res.details:
                logger.info(res.details)
        except Exception as e:  # noqa: BLE001
            results.append(TaskResult(ok=False, summary=f"{t.title}: failed", details=str(e)))
            logger.error(f"ERROR: {e}")
    return results
