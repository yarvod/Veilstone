from __future__ import annotations

import logging
import time

from voxel_sandbox.app.settings import AppSettings

LOGGER = logging.getLogger(__name__)


def run_server(
    settings: AppSettings,
    *,
    world: str,
    port: int,
    smoke_test: bool = False,
) -> int:
    del settings
    LOGGER.info("Placeholder server listening on port %d for world %s", port, world)
    if smoke_test:
        LOGGER.info("Server smoke test complete")
        return 0

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        LOGGER.info("Server stopped")
    return 0
