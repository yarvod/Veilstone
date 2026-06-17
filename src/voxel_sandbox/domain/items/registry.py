from __future__ import annotations

import tomllib
from collections.abc import Iterable, Iterator
from pathlib import Path
from types import MappingProxyType

from voxel_sandbox.domain.items.definitions import ItemDef, ItemStack, ItemType


class ItemRegistry:
    def __init__(
        self,
        definitions: Iterable[ItemDef],
        *,
        block_drops: dict[int, ItemStack] | None = None,
    ) -> None:
        by_id: dict[int, ItemDef] = {}
        by_key: dict[str, ItemDef] = {}
        by_block: dict[int, ItemDef] = {}
        for definition in definitions:
            if definition.id in by_id:
                raise ValueError(f"Duplicate item ID: {definition.id}")
            if definition.key in by_key:
                raise ValueError(f"Duplicate item key: {definition.key}")
            if definition.block_id is not None:
                if definition.block_id in by_block:
                    raise ValueError(f"Duplicate block item for block ID: {definition.block_id}")
                by_block[definition.block_id] = definition
            by_id[definition.id] = definition
            by_key[definition.key] = definition
        self._by_id = MappingProxyType(by_id)
        self._by_key = MappingProxyType(by_key)
        self._by_block = MappingProxyType(by_block)
        self._block_drops = MappingProxyType(dict(block_drops or {}))

    def by_id(self, item_id: int) -> ItemDef:
        try:
            return self._by_id[item_id]
        except KeyError as error:
            raise KeyError(f"Unknown item ID: {item_id}") from error

    def by_key(self, key: str) -> ItemDef:
        try:
            return self._by_key[key]
        except KeyError as error:
            raise KeyError(f"Unknown item key: {key}") from error

    def for_block(self, block_id: int) -> ItemDef | None:
        return self._by_block.get(block_id)

    def drop_for_block(self, block_id: int) -> ItemStack | None:
        return self._block_drops.get(block_id)

    def __iter__(self) -> Iterator[ItemDef]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)


def load_item_registry_from_toml(path: Path) -> ItemRegistry:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    next_id = 1
    definitions: list[ItemDef] = []
    for raw in data.get("item", []):
        item_id = raw.get("id", next_id)
        next_id = item_id + 1
        definitions.append(
            ItemDef(
                item_id,
                raw["key"],
                raw["name"],
                ItemType(raw["item_type"]),
                max_stack=raw.get("max_stack", 64),
                block_id=raw.get("block_id"),
            )
        )
    drops = {
        d["block_id"]: ItemStack(d["item_id"], d.get("count", 1))
        for d in data.get("drop", [])
    }
    return ItemRegistry(definitions, block_drops=drops)


def create_core_item_registry() -> ItemRegistry:
    definitions = (
        ItemDef(1, "stone", "Stone", ItemType.BLOCK, block_id=1),
        ItemDef(2, "dirt", "Dirt", ItemType.BLOCK, block_id=2),
        ItemDef(3, "grass", "Grass", ItemType.BLOCK, block_id=3),
        ItemDef(4, "veilwood_log", "Veilwood Log", ItemType.BLOCK, block_id=4),
        ItemDef(5, "veilwood_leaves", "Veilwood Leaves", ItemType.BLOCK, block_id=5),
        ItemDef(6, "dusk_crystal", "Dusk Crystal", ItemType.RESOURCE),
        ItemDef(7, "gloam_lantern", "Gloam Lantern", ItemType.BLOCK, block_id=7),
        ItemDef(8, "water_vessel", "Water Vessel", ItemType.FLUID_CONTAINER, max_stack=1),
        ItemDef(9, "veilwood_planks", "Veilwood Planks", ItemType.BLOCK, block_id=9),
        ItemDef(10, "workbench", "Runecraft Table", ItemType.BLOCK, block_id=10),
    )
    drops = {
        1: ItemStack(1, 1),
        2: ItemStack(2, 1),
        3: ItemStack(3, 1),
        4: ItemStack(4, 1),
        5: ItemStack(5, 1),
        6: ItemStack(6, 1),
        7: ItemStack(7, 1),
        9: ItemStack(9, 1),
        10: ItemStack(10, 1),
    }
    return ItemRegistry(definitions, block_drops=drops)
