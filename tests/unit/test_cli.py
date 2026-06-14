from __future__ import annotations

from voxel_sandbox.__main__ import build_parser


def test_cli_defaults_to_client() -> None:
    parser = build_parser()
    assert parser.parse_args([]).command is None


def test_developer_benchmark_commands_are_registered() -> None:
    parser = build_parser()
    for command in (
        "benchmark-mesher",
        "benchmark-worldgen",
        "benchmark-physics",
        "benchmark-lighting",
        "benchmark-streaming",
        "benchmark-frame-streaming",
        "benchmark-network",
        "benchmark-server",
        "benchmark-shadows",
    ):
        assert parser.parse_args([command]).command == command


def test_client_accepts_connect_address_and_nickname() -> None:
    args = build_parser().parse_args(
        ["client", "--connect", "127.0.0.1:25565", "--name", "Veilwalker"]
    )

    assert args.connect == "127.0.0.1:25565"
    assert args.name == "Veilwalker"
