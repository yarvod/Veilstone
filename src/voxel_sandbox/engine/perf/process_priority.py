from __future__ import annotations

import ctypes
import os
from contextlib import suppress
from typing import Any

_BELOW_NORMAL_PRIORITY_CLASS = 0x00004000


def lower_background_process_priority(increment: int = 5) -> None:
    """Yield CPU scheduling priority to the frame-owning parent process."""
    if os.name == "nt":
        with suppress(AttributeError, OSError):
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            _lower_windows_process_priority(kernel32)
        return
    nice = getattr(os, "nice", None)
    if nice is None:
        return
    with suppress(OSError):
        nice(increment)


def _lower_windows_process_priority(kernel32: Any) -> bool:
    process = kernel32.GetCurrentProcess()
    return bool(kernel32.SetPriorityClass(process, _BELOW_NORMAL_PRIORITY_CLASS))
