from __future__ import annotations

import pytest

from voxel_sandbox.app.commands import (
    CommandError,
    HelpCommand,
    ListStructuresCommand,
    ResourcePackCommand,
    SetDifficultyCommand,
    SetTimeCommand,
    SpawnStructureCommand,
    ToggleStructureCommand,
    parse_command,
)


def test_time_command_accepts_minecraft_names_and_ticks() -> None:
    assert parse_command("/time set dawn") == SetTimeCommand(23000 / 24000, "dawn")
    assert parse_command("/time set sunrise") == SetTimeCommand(0.0, "sunrise")
    assert parse_command("/time set day") == SetTimeCommand(1000 / 24000, "day")
    assert parse_command("/time set morning") == SetTimeCommand(4320 / 24000, "morning")
    assert parse_command("/time set late_sunrise") == SetTimeCommand(4320 / 24000, "late_sunrise")
    assert parse_command("/time set noon") == SetTimeCommand(0.25, "noon")
    assert parse_command("/time set night") == SetTimeCommand(13000 / 24000, "night")
    assert parse_command("/time set twilight") == SetTimeCommand(
        13800 / 24000, "twilight", freeze=True
    )
    assert parse_command("/time set 30000") == SetTimeCommand(0.25, "6000")


def test_difficulty_and_help_commands_parse() -> None:
    assert parse_command("/difficulty peaceful") == SetDifficultyCommand("peaceful")
    assert parse_command("help") == HelpCommand()


def test_resource_pack_commands_parse() -> None:
    assert parse_command("/resourcepack default") == ResourcePackCommand(None)
    command = parse_command("/resourcepack resource_packs/Faithful-32x-1.21.11")
    assert command == ResourcePackCommand("resource_packs/Faithful-32x-1.21.11")


def test_structure_debug_commands_parse() -> None:
    assert parse_command("/structure spawn gate") == SpawnStructureCommand("gate")
    assert parse_command("/structure toggle 7") == ToggleStructureCommand(7)
    assert parse_command("/structure list") == ListStructuresCommand()


@pytest.mark.parametrize(
    "source",
    ["/difficulty hard", "/time day", "/time set soon", "/unknown"],
)
def test_invalid_commands_report_a_command_error(source: str) -> None:
    with pytest.raises(CommandError):
        parse_command(source)
