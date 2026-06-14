from __future__ import annotations

import pytest

from voxel_sandbox.app.commands import (
    CommandError,
    HelpCommand,
    SetDifficultyCommand,
    SetTimeCommand,
    parse_command,
)


def test_time_command_accepts_minecraft_names_and_ticks() -> None:
    assert parse_command("/time set day") == SetTimeCommand(0.25, "day")
    assert parse_command("/time set noon") == SetTimeCommand(0.25, "noon")
    assert parse_command("/time set night") == SetTimeCommand(13000 / 24000, "night")
    assert parse_command("/time set 30000") == SetTimeCommand(0.25, "6000")


def test_difficulty_and_help_commands_parse() -> None:
    assert parse_command("/difficulty peaceful") == SetDifficultyCommand("peaceful")
    assert parse_command("help") == HelpCommand()


@pytest.mark.parametrize(
    "source",
    ["/difficulty hard", "/time day", "/time set soon", "/unknown"],
)
def test_invalid_commands_report_a_command_error(source: str) -> None:
    with pytest.raises(CommandError):
        parse_command(source)
