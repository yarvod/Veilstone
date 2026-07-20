from __future__ import annotations

import os
from contextlib import suppress


def lower_background_process_priority(increment: int = 5) -> None:
    """Yield CPU scheduling priority to the frame-owning parent process."""
    nice = getattr(os, "nice", None)
    if nice is None:
        return
    with suppress(OSError):
        nice(increment)
