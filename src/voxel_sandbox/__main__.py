from __future__ import annotations

import argparse
import multiprocessing
from collections.abc import Sequence

from voxel_sandbox import __version__
from voxel_sandbox.app.bootstrap import run_command
from voxel_sandbox.app.crash_reporting import install_crash_reporting


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voxel", description="Voxel Sandbox engine")
    parser.add_argument("--version", action="version", version=f"Veilstone {__version__}")
    parser.add_argument("--verify-package", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command")

    client = subparsers.add_parser("client", help="Start the graphical client")
    client.add_argument("--connect", metavar="HOST:PORT")
    client.add_argument("--name", default="Player", help="LAN player nickname")
    client.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)

    server = subparsers.add_parser("server", help="Start a dedicated server")
    server.add_argument("--world", default=None)
    server.add_argument("--port", type=int, default=25565)
    server.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)

    subparsers.add_parser("benchmark-mesher", help="Run the section meshing benchmark")
    subparsers.add_parser("benchmark-worldgen", help="Run the world generation benchmark")
    subparsers.add_parser("benchmark-physics", help="Run the player physics benchmark")
    subparsers.add_parser("benchmark-lighting", help="Run the chunk lighting benchmark")
    subparsers.add_parser("benchmark-streaming", help="Run the chunk integration benchmark")
    frame_streaming = subparsers.add_parser(
        "benchmark-frame-streaming", help="Run the rendered chunk streaming benchmark"
    )
    frame_streaming.add_argument("--render-distance", type=int, default=None)
    frame_streaming.add_argument("--frames", type=int, default=240)
    frame_streaming.add_argument("--warmup-frames", type=int, default=30)
    subparsers.add_parser("benchmark-network", help="Run the network protocol benchmark")
    subparsers.add_parser("benchmark-server", help="Run the multiplayer server tick benchmark")
    subparsers.add_parser("benchmark-shadows", help="Run the medium shadow frame benchmark")
    structure_preview = subparsers.add_parser(
        "structure-preview", help="Print a validated structure template by layer"
    )
    structure_preview.add_argument("template")
    subparsers.add_parser(
        "foliage-smoke-scene",
        help="Print the transparent foliage manual smoke-test scene",
    )
    reference_scene = subparsers.add_parser(
        "reference-gameplay-scene",
        help="Print deterministic reference gameplay scene summary",
    )
    reference_scene.add_argument("--metadata", default=None)
    reference_scene.add_argument("--seed", type=int, default=1337)
    reference_scene.add_argument("--resource-pack", default="default")
    reference_scene.add_argument("--render-distance", type=int, default=3)
    reference_scene.add_argument("--settings-profile", default="dev-reference")
    reference_screenshot = subparsers.add_parser(
        "reference-gameplay-screenshot",
        help="Capture the deterministic reference gameplay scene",
    )
    reference_screenshot.add_argument("--seed", type=int, default=1337)
    reference_screenshot.add_argument("--resource-pack", default="default")
    reference_screenshot.add_argument("--render-distance", type=int, default=2)
    reference_screenshot.add_argument("--output-dir", default=None)
    gameplay_smoke = subparsers.add_parser(
        "gameplay-smoke-screenshot",
        help="Capture a deterministic gameplay walking smoke screenshot",
    )
    gameplay_smoke.add_argument("--frames", type=int, default=90)
    gameplay_smoke.add_argument("--render-distance", type=int, default=None)
    gameplay_smoke.add_argument("--metadata", default=None)
    shadow_smoke = subparsers.add_parser(
        "shadow-preset-smoke",
        help="Capture shadow quality preset comparison screenshots",
    )
    shadow_smoke.add_argument("--frames", type=int, default=100)
    shadow_smoke.add_argument("--render-distance", type=int, default=2)
    shadow_smoke.add_argument("--output-dir", default=None)
    water_smoke = subparsers.add_parser(
        "water-surface-smoke",
        help="Capture deterministic water quality and buoyancy smoke evidence",
    )
    water_smoke.add_argument("--frames", type=int, default=180)
    water_smoke.add_argument("--render-distance", type=int, default=2)
    water_smoke.add_argument("--output-dir", default=None)
    inventory_smoke = subparsers.add_parser(
        "inventory-interaction-smoke",
        help="Capture deterministic inventory interaction smoke evidence",
    )
    inventory_smoke.add_argument(
        "--scenario",
        choices=(
            "icons",
            "crafting-result",
            "crafting-input",
            "right-drag",
            "left-drag",
            "right-click-split",
        ),
        default="icons",
    )
    inventory_smoke.add_argument("--output-dir", default=None)
    input_lifecycle_smoke = subparsers.add_parser(
        "input-lifecycle-smoke",
        help="Run visible movement and mouse input lifecycle verification",
    )
    input_lifecycle_smoke.add_argument("--output-dir", default=None)
    first_click_smoke = subparsers.add_parser(
        "first-click-smoke",
        help="Run visible cold-launch first-click verification",
    )
    first_click_smoke.add_argument("--initial-motion", action="store_true")
    first_click_smoke.add_argument("--output-dir", default=None)
    swim_audio_smoke = subparsers.add_parser(
        "swim-audio-smoke",
        help="Run visible swimming cadence and audio verification",
    )
    swim_audio_smoke.add_argument("--output-dir", default=None)
    check_update = subparsers.add_parser(
        "check-update",
        help="Check the latest Veilstone GitHub release",
    )
    check_update.add_argument("--repo", default=None, help=argparse.SUPPRESS)
    download_update = subparsers.add_parser(
        "download-update",
        help="Download the latest matching Veilstone release zip",
    )
    download_update.add_argument("--repo", default=None, help=argparse.SUPPRESS)
    download_update.add_argument("--output-dir", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    install_crash_reporting()
    args = build_parser().parse_args(argv)
    if args.verify_package:
        from voxel_sandbox.app.package_verification import verify_package

        return verify_package()
    if args.command is None:
        args.command = "client"
    return run_command(args)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
