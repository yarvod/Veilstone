from __future__ import annotations

from collections.abc import Iterable, Iterator
from types import MappingProxyType

from voxel_sandbox.domain.blocks.definitions import BlockDef, Material


class BlockRegistry:
    def __init__(self, definitions: Iterable[BlockDef]) -> None:
        by_id: dict[int, BlockDef] = {}
        by_key: dict[str, BlockDef] = {}
        for definition in definitions:
            if definition.id in by_id:
                raise ValueError(f"Duplicate block ID: {definition.id}")
            if definition.key in by_key:
                raise ValueError(f"Duplicate block key: {definition.key}")
            by_id[definition.id] = definition
            by_key[definition.key] = definition
        if 0 not in by_id or by_id[0].key != "air":
            raise ValueError("Block ID 0 must be registered as air")
        self._by_id = MappingProxyType(by_id)
        self._by_key = MappingProxyType(by_key)

    def by_id(self, block_id: int) -> BlockDef:
        try:
            return self._by_id[block_id]
        except KeyError as error:
            raise KeyError(f"Unknown block ID: {block_id}") from error

    def by_key(self, key: str) -> BlockDef:
        try:
            return self._by_key[key]
        except KeyError as error:
            raise KeyError(f"Unknown block key: {key}") from error

    def __iter__(self) -> Iterator[BlockDef]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)


def create_core_block_registry() -> BlockRegistry:
    return BlockRegistry(
        (
            BlockDef(
                0,
                "air",
                "Air",
                Material.AIR,
                hardness=0.0,
                is_solid=False,
                is_opaque=False,
                is_transparent=True,
            ),
            BlockDef(
                1,
                "stone",
                "Stone",
                Material.STONE,
                1.5,
                texture_top="stone",
                texture_side="stone",
                texture_bottom="stone",
            ),
            BlockDef(
                2,
                "dirt",
                "Dirt",
                Material.EARTH,
                0.5,
                texture_top="dirt",
                texture_side="dirt",
                texture_bottom="dirt",
            ),
            BlockDef(
                3,
                "grass",
                "Grass",
                Material.EARTH,
                0.6,
                texture_top="grass_top",
                texture_side="grass_side",
                texture_bottom="dirt",
            ),
            BlockDef(
                4,
                "veilwood_log",
                "Veilwood Log",
                Material.WOOD,
                1.8,
                texture_top="veilwood_cut",
                texture_side="veilwood_bark",
                texture_bottom="veilwood_cut",
            ),
            BlockDef(
                5,
                "veilwood_leaves",
                "Veilwood Leaves",
                Material.PLANT,
                0.2,
                texture_top="veilwood_leaves",
                texture_side="veilwood_leaves",
                texture_bottom="veilwood_leaves",
            ),
            BlockDef(
                6,
                "dusk_crystal_ore",
                "Dusk Crystal Ore",
                Material.STONE,
                3.0,
                texture_top="dusk_crystal_ore",
                texture_side="dusk_crystal_ore",
                texture_bottom="dusk_crystal_ore",
            ),
            BlockDef(
                7,
                "gloam_lantern",
                "Gloam Lantern",
                Material.LIGHT,
                0.1,
                is_solid=False,
                is_opaque=False,
                is_transparent=True,
                emits_light=14,
                texture_top="gloam_lantern",
                texture_side="gloam_lantern",
                texture_bottom="gloam_lantern",
            ),
            BlockDef(
                8,
                "water",
                "Water",
                Material.FLUID,
                hardness=0.0,
                is_solid=False,
                is_opaque=False,
                is_transparent=True,
                is_fluid=True,
                texture_top="water",
                texture_side="water",
                texture_bottom="water",
            ),
            BlockDef(
                9,
                "veilwood_planks",
                "Veilwood Planks",
                Material.WOOD,
                1.2,
                texture_top="veilwood_planks",
                texture_side="veilwood_planks",
                texture_bottom="veilwood_planks",
            ),
            BlockDef(
                10,
                "workbench",
                "Runecraft Table",
                Material.WOOD,
                1.8,
                texture_top="runecraft_top",
                texture_side="runecraft_side",
                texture_bottom="veilwood_planks",
            ),
            BlockDef(
                11,
                "glowing_mushroom",
                "Glowing Mushroom",
                Material.PLANT,
                0.0,
                is_solid=False,
                is_opaque=False,
                is_transparent=True,
                emits_light=10,
                texture_top="glowing_mushroom",
                texture_side="glowing_mushroom",
                texture_bottom="glowing_mushroom",
            ),
            BlockDef(
                12,
                "fireflies",
                "Twilight Fireflies",
                Material.LIGHT,
                0.0,
                is_solid=False,
                is_opaque=False,
                is_transparent=True,
                emits_light=6,
                texture_top="fireflies",
                texture_side="fireflies",
                texture_bottom="fireflies",
            ),
        )
    )
