from __future__ import annotations

import argparse
from collections.abc import Sequence

from voxel_sandbox.app.bootstrap import run_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voxel", description="Voxel Sandbox engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    client = subparsers.add_parser("client", help="Start the graphical client")
    client.add_argument("--connect", metavar="HOST:PORT")
    client.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)

    server = subparsers.add_parser("server", help="Start a dedicated server")
    server.add_argument("--world", default="saves/dev_world")
    server.add_argument("--port", type=int, default=25565)
    server.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)

    host = subparsers.add_parser("host", help="Start a local server and client")
    host.add_argument("--world", default="saves/dev_world")
    host.add_argument("--players", type=int, default=8)
    host.add_argument("--port", type=int, default=25565)
    host.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)

    subparsers.add_parser("benchmark-mesher", help="Run the section meshing benchmark")
    subparsers.add_parser("benchmark-worldgen", help="Run the world generation benchmark")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
