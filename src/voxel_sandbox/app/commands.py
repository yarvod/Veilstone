from __future__ import annotations

from dataclasses import dataclass


class CommandError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SetTimeCommand:
    time_of_day: float
    label: str
    freeze: bool = False


@dataclass(frozen=True, slots=True)
class SetDifficultyCommand:
    difficulty: str


@dataclass(frozen=True, slots=True)
class ResourcePackCommand:
    path: str | None


@dataclass(frozen=True, slots=True)
class HelpCommand:
    pass


@dataclass(frozen=True, slots=True)
class SpawnStructureCommand:
    key: str


@dataclass(frozen=True, slots=True)
class ToggleStructureCommand:
    entity_id: int


@dataclass(frozen=True, slots=True)
class ListStructuresCommand:
    pass


@dataclass(frozen=True, slots=True)
class TeleportCommand:
    target_name: str


type GameCommand = (
    SetTimeCommand
    | SetDifficultyCommand
    | ResourcePackCommand
    | HelpCommand
    | SpawnStructureCommand
    | ToggleStructureCommand
    | ListStructuresCommand
    | TeleportCommand
)

_NAMED_TIMES = {
    "sunrise": 0,
    "day": 6000,
    "noon": 6000,
    "twilight": 13800,
    "sunset": 12000,
    "night": 13000,
    "midnight": 18000,
}


def parse_command(source: str) -> GameCommand:
    parts = source.strip().removeprefix("/").split()
    if not parts:
        raise CommandError("Enter a command. Use /help for available commands.")
    command = parts[0].casefold()
    raw_arguments = parts[1:]
    arguments = [part.casefold() for part in raw_arguments]
    if command == "help" and not arguments:
        return HelpCommand()
    if command == "time" and len(arguments) == 2 and arguments[0] == "set":
        return _parse_time(arguments[1])
    if command == "difficulty" and len(arguments) == 1:
        difficulty = arguments[0]
        if difficulty not in {"peaceful", "normal"}:
            raise CommandError("Difficulty must be peaceful or normal.")
        return SetDifficultyCommand(difficulty)
    if command == "resourcepack" and len(arguments) == 1:
        if arguments[0] == "default":
            return ResourcePackCommand(None)
        return ResourcePackCommand(raw_arguments[0])
    if command == "structure" and arguments[:1] == ["spawn"] and len(arguments) == 2:
        key = arguments[1]
        if key not in {"gate", "altar", "bridge"}:
            raise CommandError("Structure must be gate, altar or bridge.")
        return SpawnStructureCommand(key)
    if command == "structure" and arguments[:1] == ["toggle"] and len(arguments) == 2:
        try:
            entity_id = int(arguments[1])
        except ValueError as error:
            raise CommandError("Structure id must be an integer.") from error
        return ToggleStructureCommand(entity_id)
    if command == "structure" and arguments == ["list"]:
        return ListStructuresCommand()
    if command == "tp" and len(arguments) == 1:
        return TeleportCommand(arguments[0])
    raise CommandError(f"Unknown command: {source.strip()}. Use /help.")


def _parse_time(value: str) -> SetTimeCommand:
    named_ticks = _NAMED_TIMES.get(value)
    if named_ticks is not None:
        return SetTimeCommand(named_ticks / 24000.0, value, freeze=(value == "twilight"))
    try:
        ticks = int(value)
    except ValueError as error:
        raise CommandError("Time must be a name or an integer tick value.") from error
    normalized_ticks = ticks % 24000
    return SetTimeCommand(normalized_ticks / 24000.0, str(normalized_ticks))
