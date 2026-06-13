from __future__ import annotations

import logging
import time

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.network import LanServer

LOGGER = logging.getLogger(__name__)


def run_server(
    settings: AppSettings,
    *,
    world: str,
    port: int,
    smoke_test: bool = False,
) -> int:
    server = LanServer("0.0.0.0", 0 if smoke_test else port, seed=settings.world.seed)
    server.start()
    LOGGER.info("Dedicated server listening on port %d for world %s", server.address[1], world)
    if smoke_test:
        server.stop()
        LOGGER.info("Server smoke test complete")
        return 0

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        LOGGER.info("Server stopped")
    finally:
        server.stop()
    return 0
