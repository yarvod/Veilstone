from __future__ import annotations

import tomllib
from collections.abc import Iterable, Iterator
from pathlib import Path
from types import MappingProxyType

from voxel_sandbox.domain.blocks.definitions import BlockDef, Material

_BLOCK_KEY_ALIASES = {
    "grass": "grass_block",
    "gloam_lantern": "lantern",
    "veilwood_log": "oak_log",
    "veilwood_leaves": "oak_leaves",
    "veilwood_planks": "oak_planks",
    "workbench": "crafting_table",
    "tall_grass": "short_grass",
}


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
        for alias, target in _BLOCK_KEY_ALIASES.items():
            if alias not in by_key and target in by_key:
                by_key[alias] = by_key[target]
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


def load_block_registry_from_toml(path: Path) -> BlockRegistry:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    next_id = 0
    definitions: list[BlockDef] = []
    for raw in data.get("block", []):
        block_id = raw.get("id", next_id)
        next_id = block_id + 1
        definitions.append(
            BlockDef(
                block_id,
                raw["key"],
                raw["name"],
                Material(raw["material"]),
                raw.get("hardness", 0.0),
                is_solid=raw.get("is_solid", True),
                is_opaque=raw.get("is_opaque", True),
                is_transparent=raw.get("is_transparent", False),
                is_fluid=raw.get("is_fluid", False),
                emits_light=raw.get("emits_light", 0),
                texture_top=raw.get("texture_top", "missing"),
                texture_side=raw.get("texture_side", "missing"),
                texture_bottom=raw.get("texture_bottom", "missing"),
                render_layer=raw.get("render_layer", "opaque"),
                render_shape=raw.get("render_shape", "cube"),
            )
        )
    return BlockRegistry(definitions)


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
                texture_top="minecraft:block/stone",
                texture_side="minecraft:block/stone",
                texture_bottom="minecraft:block/stone",
            ),
            BlockDef(
                2,
                "dirt",
                "Dirt",
                Material.EARTH,
                0.5,
                texture_top="minecraft:block/dirt",
                texture_side="minecraft:block/dirt",
                texture_bottom="minecraft:block/dirt",
            ),
            BlockDef(
                3,
                "grass_block",
                "Grass Block",
                Material.EARTH,
                0.6,
                texture_top="minecraft:block/grass_block_top",
                texture_side="minecraft:block/grass_block_side",
                texture_bottom="minecraft:block/dirt",
            ),
            BlockDef(
                4,
                "oak_log",
                "Oak Log",
                Material.WOOD,
                1.8,
                texture_top="minecraft:block/oak_log_top",
                texture_side="minecraft:block/oak_log",
                texture_bottom="minecraft:block/oak_log_top",
            ),
            BlockDef(
                5,
                "oak_leaves",
                "Oak Leaves",
                Material.PLANT,
                0.2,
                is_opaque=False,
                is_transparent=True,
                texture_top="minecraft:block/oak_leaves",
                texture_side="minecraft:block/oak_leaves",
                texture_bottom="minecraft:block/oak_leaves",
                render_layer="cutout",
            ),
            BlockDef(
                6,
                "dusk_crystal_ore",
                "Dusk Crystal Ore",
                Material.STONE,
                3.0,
                texture_top="minecraft:block/diamond_ore",
                texture_side="minecraft:block/diamond_ore",
                texture_bottom="minecraft:block/diamond_ore",
            ),
            BlockDef(
                7,
                "lantern",
                "Lantern",
                Material.LIGHT,
                0.1,
                is_solid=False,
                is_opaque=False,
                is_transparent=True,
                emits_light=14,
                texture_top="minecraft:block/lantern",
                texture_side="minecraft:block/lantern",
                texture_bottom="minecraft:block/lantern",
                render_layer="cutout",
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
                texture_top="minecraft:block/water_still",
                texture_side="minecraft:block/water_still",
                texture_bottom="minecraft:block/water_still",
            ),
            BlockDef(
                9,
                "oak_planks",
                "Oak Planks",
                Material.WOOD,
                1.2,
                texture_top="minecraft:block/oak_planks",
                texture_side="minecraft:block/oak_planks",
                texture_bottom="minecraft:block/oak_planks",
            ),
            BlockDef(
                10,
                "crafting_table",
                "Crafting Table",
                Material.WOOD,
                1.8,
                texture_top="minecraft:block/crafting_table_top",
                texture_side="minecraft:block/crafting_table_side",
                texture_bottom="minecraft:block/oak_planks",
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
                texture_top="minecraft:block/red_mushroom",
                texture_side="minecraft:block/red_mushroom",
                texture_bottom="minecraft:block/red_mushroom",
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
                texture_top="minecraft:block/glow_lichen",
                texture_side="minecraft:block/glow_lichen",
                texture_bottom="minecraft:block/glow_lichen",
            ),
            BlockDef(
                13,
                "short_grass",
                "Short Grass",
                Material.PLANT,
                0.0,
                is_solid=False,
                is_opaque=False,
                is_transparent=True,
                texture_top="minecraft:block/short_grass",
                texture_side="minecraft:block/short_grass",
                texture_bottom="minecraft:block/short_grass",
                render_layer="cutout",
                render_shape="cross",
            ),
            BlockDef(
                14,
                "wildflower",
                "Wildflower",
                Material.PLANT,
                0.0,
                is_solid=False,
                is_opaque=False,
                is_transparent=True,
                texture_top="minecraft:block/dandelion",
                texture_side="minecraft:block/dandelion",
                texture_bottom="minecraft:block/dandelion",
                render_layer="cutout",
                render_shape="cross",
            ),
        )
    )
