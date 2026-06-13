from __future__ import annotations

import logging

from voxel_sandbox.app.settings import AppSettings

LOGGER = logging.getLogger(__name__)


def run_host(
    settings: AppSettings,
    *,
    world: str,
    port: int,
    players: int,
    smoke_test: bool = False,
) -> int:
    del settings
    LOGGER.info(
        "Placeholder host started for world %s on port %d (max players: %d)",
        world,
        port,
        players,
    )
    if smoke_test:
        LOGGER.info("Host smoke test complete")
        return 0
    LOGGER.info("Graphical local client will be attached by the next Phase 1 item")
    return 0
