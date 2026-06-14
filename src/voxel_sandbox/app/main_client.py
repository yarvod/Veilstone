from __future__ import annotations

import logging

from voxel_sandbox.app.bootstrap import describe_runtime
from voxel_sandbox.app.settings import AppSettings

LOGGER = logging.getLogger(__name__)


def run_client(
    settings: AppSettings,
    *,
    smoke_test: bool = False,
    connect: str | None = None,
) -> int:
    LOGGER.info("Starting client shell: %s", describe_runtime(settings))
    from voxel_sandbox.render.window import run_window

    if smoke_test:
        run_window(settings, smoke_test=True, connect=connect)
        LOGGER.info("Client smoke test complete")
        return 0
    run_window(settings, connect=connect)
    return 0
