from __future__ import annotations

import contextvars
import os
import re
import subprocess
import threading
from typing import Callable, Iterable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict


class CommandResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    argv: list[str]
    returncode: int
    stdout: str
    stderr: str


_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
# Box-drawing/spinner glyphs that interactive CLIs (e.g. `npx skills`) redraw in place.
_SPINNER_RE = re.compile(r"^[\s│┌└├╮╯╭╰─◇◆◒◐◓◑●○■□▲▼◢◣◤◥…\.]*$")


def strip_terminal_noise(text: str) -> str:
    """Drop ANSI escapes and in-place redraw frames so captured CLI output is readable.

    Carriage-return frames keep only their last state, and lines holding nothing but spinner or
    box-drawing glyphs are removed.
    """
    lines: list[str] = []
    for raw in _ANSI_RE.sub("", text).split("\n"):
        frames = [f for f in raw.split("\r") if f.strip()]
        line = frames[-1].rstrip() if frames else ""
        if line and not _SPINNER_RE.match(line):
            lines.append(line)
    return "\n".join(lines)


# Ask interactive CLIs for plain, non-animated output; the TUI shows it in a log, not a terminal.
QUIET_ENV: dict[str, str] = {"NO_COLOR": "1", "TERM": "dumb", "CI": "1"}


_stream_sink: contextvars.ContextVar[Callable[[str], None] | None] = contextvars.ContextVar(
    "personal_os_setup_commands_stream_sink", default=None
)


def set_stream_sink(
    sink: Callable[[str], None] | None,
) -> contextvars.Token[Callable[[str], None] | None]:
    """Set a per-context sink to receive streaming subprocess output lines."""
    return _stream_sink.set(sink)


def reset_stream_sink(token: contextvars.Token[Callable[[str], None] | None]) -> None:
    """Reset the streaming sink to a previous value."""
    _stream_sink.reset(token)


def run(
    argv: Sequence[str],
    *,
    check: bool = False,
    capture_output: bool = True,
    text: bool = True,
    env: Mapping[str, str] | None = None,
) -> CommandResult:
    """Run `argv`, streaming cleaned lines to the context's sink; `env` extends os.environ."""
    sink = _stream_sink.get()
    full_env = {**os.environ, **env} if env is not None else None

    # If a sink is configured (typically by the TermTk JobRunner worker thread), stream output
    # line-by-line while still collecting stdout/stderr for the return value.
    if sink is not None and capture_output and text:
        proc = subprocess.Popen(
            list(argv),
            stdin=subprocess.DEVNULL,
            env=full_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        def _read_stream(stream, collect: list[str], prefix: str) -> None:  # type: ignore[no-untyped-def]
            if stream is None:
                return
            for line in stream:
                collect.append(line)
                cleaned = strip_terminal_noise(line)
                if cleaned:
                    sink(prefix + cleaned)

        t_out = threading.Thread(
            target=_read_stream, args=(proc.stdout, stdout_lines, ""), daemon=True
        )
        t_err = threading.Thread(
            target=_read_stream, args=(proc.stderr, stderr_lines, ""), daemon=True
        )
        t_out.start()
        t_err.start()

        returncode = proc.wait()
        t_out.join(timeout=1)
        t_err.join(timeout=1)

        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)

        if check and returncode != 0:
            raise subprocess.CalledProcessError(
                returncode, list(argv), output=stdout, stderr=stderr
            )

        return CommandResult(argv=list(argv), returncode=returncode, stdout=stdout, stderr=stderr)

    completed = subprocess.run(
        list(argv),
        check=False,
        env=full_env,
        capture_output=capture_output,
        text=text,
        encoding="utf-8" if text else None,
        errors="replace" if text else None,
    )
    if check and completed.returncode != 0:
        raise subprocess.CalledProcessError(
            completed.returncode, list(argv), output=completed.stdout, stderr=completed.stderr
        )
    return CommandResult(
        argv=list(argv),
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


def join_argv(argv: Iterable[str]) -> str:
    return " ".join(str(a) for a in argv)
