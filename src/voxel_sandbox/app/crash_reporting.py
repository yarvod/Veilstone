from __future__ import annotations

import sys
import traceback
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType

from voxel_sandbox.app.paths import crash_log_path

_installed = False


def write_crash_log(
    exception_type: type[BaseException],
    exception: BaseException,
    trace: TracebackType | None,
) -> Path:
    path = crash_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(f"\n[{datetime.now(UTC).isoformat()}]\n")
        traceback.print_exception(exception_type, exception, trace, file=file)
    return path


def install_crash_reporting() -> None:
    global _installed
    if _installed:
        return
    previous = sys.excepthook

    def report(
        exception_type: type[BaseException],
        exception: BaseException,
        trace: TracebackType | None,
    ) -> None:
        with suppress(OSError):
            write_crash_log(exception_type, exception, trace)
        previous(exception_type, exception, trace)

    sys.excepthook = report
    _installed = True
