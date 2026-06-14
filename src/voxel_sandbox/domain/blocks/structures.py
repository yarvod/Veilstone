from __future__ import annotations

import math
from dataclasses import dataclass
from typing import cast

type Vec3i = tuple[int, int, int]
type Box = tuple[float, float, float, float, float, float]
type StructureSnapshot = dict[str, object]


@dataclass(frozen=True, slots=True)
class StructureBlockPart:
    offset: Vec3i
    block_key: str
    moving: bool = False


@dataclass(frozen=True, slots=True)
class MultiBlockStructureDef:
    key: str
    parts: tuple[StructureBlockPart, ...]
    motion: str
    travel: float
    speed: float


@dataclass(slots=True)
class StructureEntity:
    entity_id: int
    key: str
    origin: Vec3i
    active: bool = False
    progress: float = 0.0
    revision: int = 1

    def snapshot(self) -> StructureSnapshot:
        return {
            "id": self.entity_id,
            "key": self.key,
            "origin": list(self.origin),
            "active": self.active,
            "progress": self.progress,
            "revision": self.revision,
        }

    @classmethod
    def from_snapshot(cls, raw: StructureSnapshot) -> StructureEntity:
        origin = raw.get("origin")
        if not isinstance(origin, list):
            raise ValueError("Structure origin must contain three coordinates")
        values = cast("list[object]", origin)
        if len(values) != 3:
            raise ValueError("Structure origin must contain three coordinates")
        if not all(isinstance(value, int) for value in values):
            raise ValueError("Structure origin coordinates must be integers")
        progress = raw.get("progress", 0.0)
        if not isinstance(progress, int | float) or not math.isfinite(float(progress)):
            raise ValueError("Structure progress must be finite")
        entity_id = raw.get("id")
        revision = raw.get("revision", 1)
        if not isinstance(entity_id, int) or not isinstance(revision, int):
            raise ValueError("Structure id and revision must be integers")
        return cls(
            entity_id=entity_id,
            key=str(raw["key"]),
            origin=cast("Vec3i", tuple(cast("list[int]", values))),
            active=bool(raw.get("active", False)),
            progress=max(0.0, min(float(progress), 1.0)),
            revision=max(1, revision),
        )


class StructureWorld:
    def __init__(
        self,
        definitions: tuple[MultiBlockStructureDef, ...] | None = None,
    ) -> None:
        definitions = definitions or create_core_structure_definitions()
        self.definitions = {definition.key: definition for definition in definitions}
        if len(self.definitions) != len(definitions):
            raise ValueError("Structure definition keys must be unique")
        self.entities: dict[int, StructureEntity] = {}
        self.next_entity_id = 1
        self.revision = 0
        self._collision_revision = -1
        self._collision_cache: tuple[Box, ...] = ()

    def spawn(self, key: str, origin: Vec3i) -> StructureEntity:
        if key not in self.definitions:
            raise KeyError(f"Unknown structure definition: {key}")
        entity = StructureEntity(self.next_entity_id, key, origin)
        self.next_entity_id += 1
        self.entities[entity.entity_id] = entity
        self.revision += 1
        return entity

    def toggle(self, entity_id: int) -> StructureEntity:
        entity = self.entities[entity_id]
        entity.active = not entity.active
        entity.revision += 1
        self.revision += 1
        return entity

    def update(self, delta_time: float) -> bool:
        changed = False
        for entity in self.entities.values():
            definition = self.definitions[entity.key]
            previous = entity.progress
            if definition.motion == "rotate_y" and entity.active:
                entity.progress = (entity.progress + definition.speed * delta_time) % 1.0
            elif definition.motion != "rotate_y":
                target = 1.0 if entity.active else 0.0
                step = definition.speed * delta_time
                if entity.progress < target:
                    entity.progress = min(target, entity.progress + step)
                elif entity.progress > target:
                    entity.progress = max(target, entity.progress - step)
            if abs(entity.progress - previous) > 1e-9:
                entity.revision += 1
                changed = True
        if changed:
            self.revision += 1
        return changed

    def snapshots(self) -> list[StructureSnapshot]:
        ordered = sorted(self.entities.values(), key=lambda item: item.entity_id)
        return [entity.snapshot() for entity in ordered]

    def replace_from_snapshots(self, snapshots: list[StructureSnapshot]) -> None:
        restored = [StructureEntity.from_snapshot(snapshot) for snapshot in snapshots]
        entities = {entity.entity_id: entity for entity in restored}
        if len(entities) != len(restored):
            raise ValueError("Structure snapshot ids must be unique")
        for entity in entities.values():
            if entity.key not in self.definitions:
                raise ValueError(f"Unknown saved structure definition: {entity.key}")
        self.entities = entities
        self.next_entity_id = max(entities, default=0) + 1
        self.revision += 1

    def collision_boxes(self) -> tuple[Box, ...]:
        if self._collision_revision == self.revision:
            return self._collision_cache
        boxes: list[Box] = []
        for entity in self.entities.values():
            definition = self.definitions[entity.key]
            for part in definition.parts:
                x, y, z = _part_position(definition, entity, part)
                boxes.append((x, y, z, x + 1.0, y + 1.0, z + 1.0))
        self._collision_cache = tuple(boxes)
        self._collision_revision = self.revision
        return self._collision_cache

    def is_solid_cell(self, x: int, y: int, z: int) -> bool:
        cell = (float(x), float(y), float(z), float(x + 1), float(y + 1), float(z + 1))
        return any(_boxes_overlap(cell, box) for box in self.collision_boxes())

    def raycast_entity(
        self,
        origin: tuple[float, float, float],
        direction: tuple[float, float, float],
        max_distance: float = 6.0,
    ) -> tuple[int, float] | None:
        best: tuple[int, float] | None = None
        for entity in self.entities.values():
            definition = self.definitions[entity.key]
            for part in definition.parts:
                x, y, z = _part_position(definition, entity, part)
                distance = _ray_box_distance(
                    origin,
                    direction,
                    (x, y, z, x + 1.0, y + 1.0, z + 1.0),
                    max_distance,
                )
                if distance is not None and (best is None or distance < best[1]):
                    best = entity.entity_id, distance
        return best


def structure_part_transform(
    definition: MultiBlockStructureDef,
    entity: StructureEntity,
    part: StructureBlockPart,
) -> tuple[tuple[float, float, float], float]:
    x, y, z = (float(coordinate) for coordinate in part.offset)
    if part.moving and definition.motion == "translate_y":
        y += definition.travel * entity.progress
    elif part.moving and definition.motion == "translate_x":
        x += definition.travel * entity.progress
    rotation = (
        math.tau * entity.progress if part.moving and definition.motion == "rotate_y" else 0.0
    )
    return (x, y, z), rotation


def _part_position(
    definition: MultiBlockStructureDef,
    entity: StructureEntity,
    part: StructureBlockPart,
) -> tuple[float, float, float]:
    x = float(entity.origin[0] + part.offset[0])
    y = float(entity.origin[1] + part.offset[1])
    z = float(entity.origin[2] + part.offset[2])
    if not part.moving:
        return x, y, z
    if definition.motion == "translate_y":
        y += definition.travel * entity.progress
    elif definition.motion == "translate_x":
        x += definition.travel * entity.progress
    return x, y, z


def _boxes_overlap(left: Box, right: Box) -> bool:
    epsilon = 1e-6
    return all(
        left[axis] < right[axis + 3] - epsilon and left[axis + 3] > right[axis] + epsilon
        for axis in range(3)
    )


def _ray_box_distance(
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    box: Box,
    max_distance: float,
) -> float | None:
    near = 0.0
    far = max_distance
    for axis in range(3):
        component = direction[axis]
        if abs(component) <= 1e-9:
            if not box[axis] <= origin[axis] <= box[axis + 3]:
                return None
            continue
        first = (box[axis] - origin[axis]) / component
        second = (box[axis + 3] - origin[axis]) / component
        near = max(near, min(first, second))
        far = min(far, max(first, second))
        if near > far:
            return None
    return near if near <= max_distance else None


def create_core_structure_definitions() -> tuple[MultiBlockStructureDef, ...]:
    gate_parts = tuple(
        [StructureBlockPart((-1, y, 0), "stone") for y in range(4)]
        + [StructureBlockPart((2, y, 0), "stone") for y in range(4)]
        + [StructureBlockPart((x, 3, 0), "stone") for x in range(3)]
        + [
            StructureBlockPart((x, y, 0), "veilwood_planks", moving=True)
            for x in range(2)
            for y in range(3)
        ]
    )
    altar_parts = (
        StructureBlockPart((0, 0, 0), "stone"),
        StructureBlockPart((0, 1, 0), "gloam_lantern", moving=True),
        StructureBlockPart((1, 1, 0), "dusk_crystal_ore", moving=True),
        StructureBlockPart((-1, 1, 0), "dusk_crystal_ore", moving=True),
        StructureBlockPart((0, 1, 1), "dusk_crystal_ore", moving=True),
        StructureBlockPart((0, 1, -1), "dusk_crystal_ore", moving=True),
    )
    bridge_parts = tuple(
        StructureBlockPart((x, 0, z), "veilwood_planks", moving=True)
        for x in range(3)
        for z in range(2)
    )
    return (
        MultiBlockStructureDef("gate", gate_parts, "translate_y", 3.2, 0.55),
        MultiBlockStructureDef("altar", altar_parts, "rotate_y", 0.0, 0.08),
        MultiBlockStructureDef("bridge", bridge_parts, "translate_x", 4.0, 0.35),
    )
