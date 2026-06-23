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
    server.add_argument("--world", default="saves/dev_world")
    server.add_argument("--port", type=int, default=25565)
    server.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)

    subparsers.add_parser("benchmark-mesher", help="Run the section meshing benchmark")
    subparsers.add_parser("benchmark-worldgen", help="Run the world generation benchmark")
    subparsers.add_parser("benchmark-physics", help="Run the player physics benchmark")
    subparsers.add_parser("benchmark-lighting", help="Run the chunk lighting benchmark")
    subparsers.add_parser("benchmark-streaming", help="Run the chunk integration benchmark")
    subparsers.add_parser(
        "benchmark-frame-streaming", help="Run the rendered chunk streaming benchmark"
    )
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
