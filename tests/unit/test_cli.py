from __future__ import annotations

import pytest

from voxel_sandbox.__main__ import build_parser, main


def test_cli_requires_a_command() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


@pytest.mark.parametrize("command", ["client", "server", "host"])
def test_application_smoke_commands(command: str) -> None:
    assert main([command, "--smoke-test"]) == 0
