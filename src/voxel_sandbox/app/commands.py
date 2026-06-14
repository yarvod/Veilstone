from __future__ import annotations

from dataclasses import dataclass


class CommandError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SetTimeCommand:
    time_of_day: float
    label: str


@dataclass(frozen=True, slots=True)
class SetDifficultyCommand:
    difficulty: str


@dataclass(frozen=True, slots=True)
class HelpCommand:
    pass


type GameCommand = SetTimeCommand | SetDifficultyCommand | HelpCommand

_NAMED_TIMES = {
    "sunrise": 0,
    "day": 6000,
    "noon": 6000,
    "sunset": 12000,
    "night": 13000,
    "midnight": 18000,
}


def parse_command(source: str) -> GameCommand:
    parts = source.strip().removeprefix("/").split()
    if not parts:
        raise CommandError("Enter a command. Use /help for available commands.")
    command = parts[0].casefold()
    arguments = [part.casefold() for part in parts[1:]]
    if command == "help" and not arguments:
        return HelpCommand()
    if command == "time" and len(arguments) == 2 and arguments[0] == "set":
        return _parse_time(arguments[1])
    if command == "difficulty" and len(arguments) == 1:
        difficulty = arguments[0]
        if difficulty not in {"peaceful", "normal"}:
            raise CommandError("Difficulty must be peaceful or normal.")
        return SetDifficultyCommand(difficulty)
    raise CommandError(f"Unknown command: {source.strip()}. Use /help.")


def _parse_time(value: str) -> SetTimeCommand:
    named_ticks = _NAMED_TIMES.get(value)
    if named_ticks is not None:
        return SetTimeCommand(named_ticks / 24000.0, value)
    try:
        ticks = int(value)
    except ValueError as error:
        raise CommandError("Time must be a name or an integer tick value.") from error
    normalized_ticks = ticks % 24000
    return SetTimeCommand(normalized_ticks / 24000.0, str(normalized_ticks))
