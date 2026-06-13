from __future__ import annotations

import argparse
import logging

from voxel_sandbox.app.settings import AppSettings, load_settings
from voxel_sandbox.infrastructure.logging import configure_logging

LOGGER = logging.getLogger(__name__)


def run_command(args: argparse.Namespace) -> int:
    settings = load_settings()
    configure_logging(settings.logging.level)
    LOGGER.debug("Loaded settings: %s", settings)

    command = str(args.command)
    if command == "client":
        from voxel_sandbox.app.main_client import run_client

        return run_client(settings, smoke_test=bool(args.smoke_test))
    if command == "server":
        from voxel_sandbox.app.main_server import run_server

        return run_server(
            settings,
            world=str(args.world),
            port=int(args.port),
            smoke_test=bool(args.smoke_test),
        )
    if command == "benchmark-mesher":
        LOGGER.error("Mesher benchmark is not available before Phase 4")
        return 2
    if command == "benchmark-worldgen":
        LOGGER.error("World generation benchmark is not available before Phase 5")
        return 2
    if command == "benchmark-network":
        LOGGER.error("Network benchmark is not available before Phase 13")
        return 2
    raise ValueError(f"Unsupported command: {command}")


def describe_runtime(settings: AppSettings) -> str:
    return f"{settings.window.title} {settings.window.width}x{settings.window.height}"
