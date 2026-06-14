from __future__ import annotations

import random
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from voxel_sandbox.engine.chunks import SECTION_SIZE, ChunkCoord
from voxel_sandbox.engine.generation.seed import WorldSeed

STRUCTURE_VERSION = 1
STRUCTURE_REGION_CHUNKS = 4


@dataclass(frozen=True, slots=True)
class StructureBlock:
    x: int
    y: int
    z: int
    block_id: int


@dataclass(frozen=True, slots=True)
class LootEntry:
    item_id: int
    minimum: int
    maximum: int
    weight: int


@dataclass(frozen=True, slots=True)
class StructureTemplate:
    key: str
    size: tuple[int, int, int]
    blocks: tuple[StructureBlock, ...]
    loot: tuple[LootEntry, ...] = ()
    rarity: str = "common"


@dataclass(frozen=True, slots=True)
class StructurePlacement:
    template: StructureTemplate
    origin: tuple[int, int, int]

    def intersects_chunk(self, coord: ChunkCoord) -> bool:
        min_x = coord.x * SECTION_SIZE
        min_z = coord.z * SECTION_SIZE
        max_x = min_x + SECTION_SIZE
        max_z = min_z + SECTION_SIZE
        return (
            self.origin[0] < max_x
            and self.origin[0] + self.template.size[0] > min_x
            and self.origin[2] < max_z
            and self.origin[2] + self.template.size[2] > min_z
        )


@dataclass(frozen=True, slots=True)
class StructureLootRoll:
    item_id: int
    count: int


def load_structure_templates(root: Path) -> tuple[StructureTemplate, ...]:
    templates = tuple(_load_template(path) for path in sorted(root.glob("*.toml")))
    if not templates:
        raise ValueError(f"No structure templates found in {root}")
    keys = [template.key for template in templates]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate structure template key")
    return templates


def structure_placements_for_chunk(
    coord: ChunkCoord,
    seed: WorldSeed,
    templates: tuple[StructureTemplate, ...],
    height_at: Callable[[int, int], int],
) -> tuple[StructurePlacement, ...]:
    region_x = coord.x // STRUCTURE_REGION_CHUNKS
    region_z = coord.z // STRUCTURE_REGION_CHUNKS
    placements: list[StructurePlacement] = []
    for candidate_x in range(region_x - 1, region_x + 2):
        for candidate_z in range(region_z - 1, region_z + 2):
            placement = _placement_for_region(
                candidate_x,
                candidate_z,
                seed,
                templates,
                height_at,
            )
            if placement is not None and placement.intersects_chunk(coord):
                placements.append(placement)
    return tuple(placements)


def roll_structure_loot(
    template: StructureTemplate,
    seed: WorldSeed,
    origin: tuple[int, int, int],
) -> tuple[StructureLootRoll, ...]:
    if not template.loot:
        return ()
    randomizer = random.Random(seed.value ^ _mix(origin[0], origin[2], 71))
    total_weight = sum(entry.weight for entry in template.loot)
    rolls: list[StructureLootRoll] = []
    for _ in range(min(3, len(template.loot))):
        choice = randomizer.randrange(total_weight)
        cursor = 0
        for entry in template.loot:
            cursor += entry.weight
            if choice < cursor:
                rolls.append(
                    StructureLootRoll(
                        entry.item_id,
                        randomizer.randint(entry.minimum, entry.maximum),
                    )
                )
                break
    return tuple(rolls)


def _placement_for_region(
    region_x: int,
    region_z: int,
    seed: WorldSeed,
    templates: tuple[StructureTemplate, ...],
    height_at: Callable[[int, int], int],
) -> StructurePlacement | None:
    roll = _unit_hash(seed.value, region_x, region_z, 51)
    if roll < 0.62:
        return None
    rare = tuple(template for template in templates if template.rarity == "rare")
    common = tuple(template for template in templates if template.rarity != "rare")
    choices = rare if roll > 0.985 and rare else common
    if not choices:
        return None
    template = choices[
        int(_unit_hash(seed.value, region_x, region_z, 52) * len(choices)) % len(choices)
    ]
    region_size = STRUCTURE_REGION_CHUNKS * SECTION_SIZE
    available_x = max(1, region_size - template.size[0])
    available_z = max(1, region_size - template.size[2])
    origin_x = region_x * region_size + int(
        _unit_hash(seed.value, region_x, region_z, 53) * available_x
    )
    origin_z = region_z * region_size + int(
        _unit_hash(seed.value, region_x, region_z, 54) * available_z
    )
    samples = (
        height_at(origin_x, origin_z),
        height_at(origin_x + template.size[0] - 1, origin_z),
        height_at(origin_x, origin_z + template.size[2] - 1),
        height_at(origin_x + template.size[0] - 1, origin_z + template.size[2] - 1),
    )
    if min(samples) < 32 or max(samples) - min(samples) > 3:
        return None
    return StructurePlacement(template, (origin_x, max(samples), origin_z))


def _load_template(path: Path) -> StructureTemplate:
    with path.open("rb") as file:
        raw = cast(dict[str, object], tomllib.load(file))
    if raw.get("version") != STRUCTURE_VERSION:
        raise ValueError(f"Unsupported structure version in {path}")
    key = raw.get("key")
    size = raw.get("size")
    if not isinstance(key, str) or not isinstance(size, list):
        raise ValueError(f"Invalid structure header in {path}")
    raw_size = cast(list[object], size)
    if len(raw_size) != 3 or not all(isinstance(value, int) for value in raw_size):
        raise ValueError(f"Invalid structure header in {path}")
    size_values = cast(list[int], raw_size)
    dimensions = (size_values[0], size_values[1], size_values[2])
    if any(value <= 0 for value in dimensions):
        raise ValueError(f"Invalid structure size in {path}")
    blocks: list[StructureBlock] = []
    for entry in cast(list[dict[str, object]], raw.get("blocks", [])):
        position = cast(list[int], entry["position"])
        if len(position) != 3 or not all(
            0 <= int(position[index]) < dimensions[index] for index in range(3)
        ):
            raise ValueError(f"Block outside structure bounds in {path}")
        block_id = int(cast(int, entry["block_id"]))
        if not 0 <= block_id <= 10:
            raise ValueError(f"Unknown block ID {block_id} in {path}")
        blocks.append(
            StructureBlock(int(position[0]), int(position[1]), int(position[2]), block_id)
        )
    if not blocks:
        raise ValueError(f"Structure has no blocks in {path}")
    loot = tuple(
        LootEntry(
            int(cast(int, entry["item_id"])),
            int(cast(int, entry["minimum"])),
            int(cast(int, entry["maximum"])),
            int(cast(int, entry["weight"])),
        )
        for entry in cast(list[dict[str, object]], raw.get("loot", []))
    )
    if any(
        entry.minimum < 1 or entry.maximum < entry.minimum or entry.weight < 1 for entry in loot
    ):
        raise ValueError(f"Invalid loot table in {path}")
    return StructureTemplate(
        key,
        dimensions,
        tuple(blocks),
        loot,
        str(raw.get("rarity", "common")),
    )


def _unit_hash(seed: int, x: int, z: int, channel: int) -> float:
    return (_mix(x, z, channel) ^ seed) % 1_000_003 / 1_000_003.0


def _mix(x: int, z: int, channel: int) -> int:
    value = (x * 0x9E3779B1) ^ (z * 0x85EBCA77) ^ (channel * 0xC2B2AE3D)
    value ^= value >> 16
    value *= 0x7FEB352D
    value ^= value >> 15
    return value & 0xFFFFFFFFFFFFFFFF
