from __future__ import annotations

import argparse
from collections.abc import Sequence

from voxel_sandbox.app.bootstrap import run_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voxel", description="Voxel Sandbox engine")
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command is None:
        args.command = "client"
    return run_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
