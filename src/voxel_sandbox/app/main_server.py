from __future__ import annotations

import logging
import time
from pathlib import Path

from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.audio.runtime import create_server_audio_bus
from voxel_sandbox.infrastructure.storage import WorldStorage
from voxel_sandbox.network import LanServer
from voxel_sandbox.network.discovery import DiscoveryResponder

LOGGER = logging.getLogger(__name__)


def run_server(
    settings: AppSettings,
    *,
    world: str,
    port: int,
    smoke_test: bool = False,
) -> int:
    audio = create_server_audio_bus(settings.audio)
    storage = WorldStorage(Path(world))
    storage.ensure_world(name="Veilstone Dedicated World", seed=settings.world.seed)
    server = LanServer(
        "0.0.0.0",
        0 if smoke_test else port,
        seed=settings.world.seed,
        storage=storage,
    )
    server.start()
    discovery = DiscoveryResponder(
        "0.0.0.0",
        server.address[1],
        world_name="Veilstone LAN World",
        game_port=server.address[1],
        player_count=lambda: server.player_count,
    )
    discovery.start()
    LOGGER.info("Dedicated server listening on port %d for world %s", server.address[1], world)
    if smoke_test:
        discovery.stop()
        server.stop()
        audio.close()
        LOGGER.info("Server smoke test complete")
        return 0

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        LOGGER.info("Server stopped")
    finally:
        discovery.stop()
        server.stop()
        audio.close()
    return 0
