from __future__ import annotations

import argparse
import logging
import sys

from voxel_sandbox.app.paths import user_settings_path
from voxel_sandbox.app.settings import AppSettings, load_settings, save_user_settings
from voxel_sandbox.infrastructure.logging import configure_logging

LOGGER = logging.getLogger(__name__)


def run_command(args: argparse.Namespace) -> int:
    settings = load_settings()
    if getattr(sys, "frozen", False) and not user_settings_path().exists():
        save_user_settings(settings)
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
        from voxel_sandbox.app.paths import default_server_world_path

        world = str(args.world) if args.world else str(default_server_world_path())
        return run_server(
            settings,
            world=world,
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

        return run_benchmark(
            settings,
            frames=int(getattr(args, "frames", 240)),
            warmup_frames=int(getattr(args, "warmup_frames", 30)),
            render_distance=getattr(args, "render_distance", None),
        )
    if command == "benchmark-network":
        from voxel_sandbox.tools.benchmark_network import run_benchmark

        return run_benchmark()
    if command == "benchmark-server":
        from voxel_sandbox.tools.benchmark_server import run_benchmark

        return run_benchmark()
    if command == "benchmark-shadows":
        from voxel_sandbox.tools.benchmark_shadows import run_benchmark

        return run_benchmark(settings)
    if command == "structure-preview":
        from voxel_sandbox.tools.structure_preview import run_preview

        return run_preview(str(args.template))
    if command == "foliage-smoke-scene":
        from voxel_sandbox.tools.foliage_smoke_scene import run_preview

        return run_preview()
    if command == "reference-gameplay-scene":
        from pathlib import Path

        from voxel_sandbox.tools.reference_gameplay_scene import run_preview

        metadata = getattr(args, "metadata", None)
        return run_preview(
            metadata_path=Path(str(metadata)) if metadata else None,
            seed=int(getattr(args, "seed", 1337)),
            resource_pack=str(getattr(args, "resource_pack", "default")),
            render_distance=int(getattr(args, "render_distance", 3)),
            settings_profile=str(getattr(args, "settings_profile", "dev-reference")),
        )
    if command == "gameplay-smoke-screenshot":
        from pathlib import Path

        from voxel_sandbox.tools.gameplay_smoke_screenshot import run_smoke

        metadata = getattr(args, "metadata", None)
        return run_smoke(
            settings,
            frames=int(getattr(args, "frames", 90)),
            render_distance=getattr(args, "render_distance", None),
            metadata_path=Path(str(metadata)) if metadata else None,
        )
    if command == "shadow-preset-smoke":
        from pathlib import Path

        from voxel_sandbox.tools.shadow_preset_smoke import run_shadow_preset_smoke

        output_dir = getattr(args, "output_dir", None)
        return run_shadow_preset_smoke(
            settings,
            frames=int(getattr(args, "frames", 100)),
            render_distance=int(getattr(args, "render_distance", 2)),
            output_dir=Path(str(output_dir)) if output_dir else None,
        )
    if command == "water-surface-smoke":
        from pathlib import Path

        from voxel_sandbox.tools.water_surface_smoke import run_water_surface_smoke

        output_dir = getattr(args, "output_dir", None)
        return run_water_surface_smoke(
            settings,
            frames=int(getattr(args, "frames", 180)),
            render_distance=int(getattr(args, "render_distance", 2)),
            output_dir=Path(str(output_dir)) if output_dir else None,
        )
    if command == "inventory-interaction-smoke":
        from pathlib import Path

        from voxel_sandbox.tools.inventory_interaction_smoke import (
            run_inventory_interaction_smoke,
        )

        output_dir = getattr(args, "output_dir", None)
        return run_inventory_interaction_smoke(
            settings,
            scenario=str(getattr(args, "scenario", "icons")),
            output_dir=Path(str(output_dir)) if output_dir else None,
        )
    if command == "check-update":
        from voxel_sandbox.app.updates import REPO_SLUG, run_check_update

        return run_check_update(repo_slug=str(args.repo or REPO_SLUG))
    if command == "download-update":
        from pathlib import Path

        from voxel_sandbox.app.updates import REPO_SLUG, run_download_update

        output_dir = Path(str(args.output_dir)) if args.output_dir else None
        return run_download_update(
            repo_slug=str(args.repo or REPO_SLUG),
            destination_dir=output_dir,
        )
    raise ValueError(f"Unsupported command: {command}")


def describe_runtime(settings: AppSettings) -> str:
    return f"{settings.window.title} {settings.window.width}x{settings.window.height}"
