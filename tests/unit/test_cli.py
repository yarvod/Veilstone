from __future__ import annotations

import pytest

from voxel_sandbox.__main__ import build_parser, main


def test_cli_defaults_to_client() -> None:
    parser = build_parser()
    assert parser.parse_args([]).command is None


def test_default_application_smoke_command() -> None:
    assert main(["--smoke-test"]) == 0


@pytest.mark.parametrize("command", ["client", "server"])
def test_application_smoke_commands(command: str) -> None:
    assert main([command, "--smoke-test"]) == 0


def test_developer_benchmark_commands_are_registered() -> None:
    parser = build_parser()
    for command in (
        "benchmark-mesher",
        "benchmark-worldgen",
        "benchmark-physics",
        "benchmark-lighting",
        "benchmark-network",
    ):
        assert parser.parse_args([command]).command == command
