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

        return run_client(
            settings,
            smoke_test=bool(args.smoke_test),
            connect=str(connect) if (connect := getattr(args, "connect", None)) else None,
            player_name=str(getattr(args, "name", "Player")),
        )
    if command == "server":
        from voxel_sandbox.app.main_server import run_server

        return run_server(
            settings,
            world=str(args.world),
            port=int(args.port),
            smoke_test=bool(args.smoke_test),
        )
    if command == "benchmark-mesher":
        from voxel_sandbox.tools.benchmark_mesher import run_benchmark

        return run_benchmark()
    if command == "benchmark-worldgen":
        from voxel_sandbox.tools.benchmark_worldgen import run_benchmark

        return run_benchmark()
    if command == "benchmark-physics":
        from voxel_sandbox.tools.benchmark_physics import run_benchmark

        return run_benchmark()
    if command == "benchmark-lighting":
        from voxel_sandbox.tools.benchmark_lighting import run_benchmark

        return run_benchmark()
    if command == "benchmark-streaming":
        from voxel_sandbox.tools.benchmark_streaming import run_benchmark

        return run_benchmark()
    if command == "benchmark-frame-streaming":
        from voxel_sandbox.tools.benchmark_frame_streaming import run_benchmark

        return run_benchmark(settings)
    if command == "benchmark-network":
        from voxel_sandbox.tools.benchmark_network import run_benchmark

        return run_benchmark()
    if command == "benchmark-server":
        from voxel_sandbox.tools.benchmark_server import run_benchmark

        return run_benchmark()
    raise ValueError(f"Unsupported command: {command}")


def describe_runtime(settings: AppSettings) -> str:
    return f"{settings.window.title} {settings.window.width}x{settings.window.height}"
