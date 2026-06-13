from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ItemType(Enum):
    BLOCK = "block"
    RESOURCE = "resource"
    TOOL = "tool"
    FOOD = "food"
    FLUID_CONTAINER = "fluid_container"


@dataclass(frozen=True, slots=True)
class ItemDef:
    id: int
    key: str
    name: str
    item_type: ItemType
    max_stack: int = 64
    block_id: int | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.id <= 65535:
            raise ValueError("Item ID must be between 1 and 65535")
        if not self.key or self.key.lower() != self.key:
            raise ValueError("Item key must be non-empty lowercase text")
        if not 1 <= self.max_stack <= 255:
            raise ValueError("Item max stack must be between 1 and 255")
        if self.item_type is ItemType.BLOCK and self.block_id is None:
            raise ValueError("Block items require a block ID")


@dataclass(frozen=True, slots=True)
class ItemStack:
    item_id: int
    count: int

    def __post_init__(self) -> None:
        if self.item_id < 1:
            raise ValueError("Item stack requires a positive item ID")
        if self.count < 1:
            raise ValueError("Item stack count must be positive")

    def with_count(self, count: int) -> ItemStack:
        return ItemStack(self.item_id, count)
