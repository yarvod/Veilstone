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
    LOGGER.info(
        "Placeholder host started for world %s on port %d (max players: %d)",
        world,
        port,
        players,
    )
    if smoke_test:
        from voxel_sandbox.render.window import run_window

        run_window(settings, smoke_test=True)
        LOGGER.info("Host smoke test complete")
        return 0
    LOGGER.info("Starting local client shell for placeholder host")
    from voxel_sandbox.app.main_client import run_client

    return run_client(settings)
