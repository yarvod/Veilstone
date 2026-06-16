from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TextPurpose(Enum):
    DIRECT_CONNECT = auto()
    NICKNAME = auto()
    CHAT = auto()
    COMMAND = auto()
    RENAME_WORLD = auto()
    WORLD_NAME = auto()
    WORLD_SEED = auto()
    DELETE_WORLD = auto()


@dataclass(slots=True)
class TextInput:
    purpose: TextPurpose
    prompt: str
    value: str = ""
    maximum_length: int = 128

    def append(self, text: str) -> None:
        printable = "".join(character for character in text if character.isprintable())
        self.value = (self.value + printable)[: self.maximum_length]

    def backspace(self) -> None:
        self.value = self.value[:-1]

    @property
    def display(self) -> str:
        return f"{self.prompt}\n> {self.value}_"
