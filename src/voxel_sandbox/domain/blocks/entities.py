from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

type BlockEntityData = dict[str, object]


class BlockEntity(Protocol):
    kind: str

    def snapshot(self) -> BlockEntityData: ...


@dataclass(slots=True)
class GenericBlockEntity:
    kind: str
    data: BlockEntityData = field(default_factory=lambda: {})

    def snapshot(self) -> BlockEntityData:
        return {"kind": self.kind, "data": dict(self.data)}


class BlockEntityRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, type[GenericBlockEntity]] = {}

    def register(self, key: str, factory: type[GenericBlockEntity]) -> None:
        if key in self._factories:
            raise ValueError(f"Block entity '{key}' already registered")
        self._factories[key] = factory

    def create(self, key: str, data: BlockEntityData | None = None) -> GenericBlockEntity:
        try:
            factory = self._factories[key]
        except KeyError as error:
            raise KeyError(f"Unknown block entity: {key}") from error
        return factory(key, dict(data or {}))
