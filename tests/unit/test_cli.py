from __future__ import annotations

import tomllib

from voxel_sandbox import __version__
from voxel_sandbox.__main__ import build_parser


def test_cli_defaults_to_client() -> None:
    parser = build_parser()
    assert parser.parse_args([]).command is None


def test_package_exposes_version() -> None:
    with open("pyproject.toml", "rb") as pyproject:
        metadata = tomllib.load(pyproject)
    assert __version__ == metadata["project"]["version"]


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


def test_server_world_defaults_to_application_data_root() -> None:
    args = build_parser().parse_args(["server"])
    assert args.world is None


def test_structure_preview_accepts_template_key() -> None:
    args = build_parser().parse_args(["structure-preview", "veilstone_ruin"])
    assert args.command == "structure-preview"
    assert args.template == "veilstone_ruin"


def test_update_commands_are_registered() -> None:
    parser = build_parser()
    assert parser.parse_args(["check-update"]).command == "check-update"
    args = parser.parse_args(["download-update", "--output-dir", "saves/updates"])
    assert args.command == "download-update"
    assert args.output_dir == "saves/updates"
