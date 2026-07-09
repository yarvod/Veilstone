from __future__ import annotations

import pytest

from voxel_sandbox.app.commands import (
    CommandError,
    HelpCommand,
    ListStructuresCommand,
    MaterialQualityCommand,
    ResourcePackCommand,
    SetDifficultyCommand,
    SetTimeCommand,
    SpawnStructureCommand,
    ToggleStructureCommand,
    parse_command,
)


@pytest.mark.parametrize(
    ("name", "ticks", "freeze"),
    [
        ("dawn", 23000, False),
        ("sunrise", 0, False),
        ("day", 1000, False),
        ("morning", 4320, False),
        ("late_sunrise", 4320, False),
        ("late-sunrise", 4320, False),
        ("noon", 6000, False),
        ("sunset", 12000, False),
        ("night", 13000, False),
        ("twilight", 13800, True),
        ("midnight", 18000, False),
    ],
)
def test_time_command_named_semantics_are_explicit(name: str, ticks: int, freeze: bool) -> None:
    assert parse_command(f"/time set {name}") == SetTimeCommand(ticks / 24000, name, freeze=freeze)


def test_time_command_accepts_wrapping_ticks() -> None:
    assert parse_command("/time set 30000") == SetTimeCommand(0.25, "6000")


def test_difficulty_and_help_commands_parse() -> None:
    assert parse_command("/difficulty peaceful") == SetDifficultyCommand("peaceful")
    assert parse_command("help") == HelpCommand()


def test_resource_pack_commands_parse() -> None:
    assert parse_command("/resourcepack default") == ResourcePackCommand(None)
    command = parse_command("/resourcepack resource_packs/Faithful-32x-1.21.11")
    assert command == ResourcePackCommand("resource_packs/Faithful-32x-1.21.11")


def test_material_quality_commands_parse() -> None:
    assert parse_command("/materials material-preview") == MaterialQualityCommand(
        "material-preview"
    )
    assert parse_command("/materials color-only") == MaterialQualityCommand("color-only")
    with pytest.raises(CommandError):
        parse_command("/materials ultra")


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
