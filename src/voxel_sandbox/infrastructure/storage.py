from __future__ import annotations

import json
import struct
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import numpy as np

from voxel_sandbox.domain.blocks.structures import StructureSnapshot, StructureWorld
from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemRegistry, ItemStack
from voxel_sandbox.engine.chunks import Chunk, ChunkCoord, DirtyFlag

SAVE_VERSION = 1
CHUNK_MAGIC = b"VCHK"
CHUNK_HEADER = struct.Struct("<4sHii")


@dataclass(frozen=True, slots=True)
class WorldMetadata:
    version: int
    name: str
    seed: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class PlayerSnapshot:
    position: tuple[float, float, float]
    health: float
    selected_slot: int
    slots: tuple[ItemStack | None, ...]


class WorldStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.regions = root / "regions"
        self.players = root / "players"
        self.structures = root / "structures"

    def ensure_world(self, *, name: str, seed: str) -> WorldMetadata:
        self.regions.mkdir(parents=True, exist_ok=True)
        self.players.mkdir(parents=True, exist_ok=True)
        metadata = WorldMetadata(SAVE_VERSION, name, seed, datetime.now(UTC).isoformat())
        self._atomic_write_text(
            self.root / "level.toml",
            f'version = {metadata.version}\nname = "{name}"\nseed = "{seed}"\n'
            f'updated_at = "{metadata.updated_at}"\n',
        )
        return metadata

    def rename_world(self, new_name: str) -> WorldMetadata:
        # overwrite metadata name preserving seed
        meta = self.load_metadata()
        if meta is None:
            raise ValueError("No metadata to rename")
        return self.ensure_world(name=new_name, seed=meta.seed)

    def load_metadata(self) -> WorldMetadata | None:
        import tomllib

        path = self.root / "level.toml"
        if not path.exists():
            return None
        with path.open("rb") as file:
            data = cast(dict[str, object], tomllib.load(file))
        return WorldMetadata(
            int(cast(int, data["version"])),
            str(data["name"]),
            str(data["seed"]),
            str(data["updated_at"]),
        )

    def save_chunk(self, chunk: Chunk) -> None:
        arrays: list[bytes] = []
        for section in chunk.sections:
            arrays.extend(
                (
                    section.blocks.astype("<u2", copy=False).tobytes(),
                    section.metadata.tobytes(),
                    section.sky_light.tobytes(),
                    section.block_light.tobytes(),
                )
            )
        payload = zlib.compress(b"".join(arrays), level=6)
        header = CHUNK_HEADER.pack(CHUNK_MAGIC, SAVE_VERSION, chunk.coord.x, chunk.coord.z)
        self.regions.mkdir(parents=True, exist_ok=True)
        self._atomic_write_bytes(self._chunk_path(chunk.coord), header + payload)
        for section in chunk.sections:
            section.clear_dirty(DirtyFlag.SAVE)

    def load_chunk(self, coord: ChunkCoord) -> Chunk | None:
        path = self._chunk_path(coord)
        if not path.exists():
            return None
        data = path.read_bytes()
        magic, version, chunk_x, chunk_z = CHUNK_HEADER.unpack_from(data)
        if magic != CHUNK_MAGIC:
            raise ValueError(f"Invalid chunk magic in {path}")
        if version != SAVE_VERSION:
            data = migrate_chunk(data, version, SAVE_VERSION)
            magic, version, chunk_x, chunk_z = CHUNK_HEADER.unpack_from(data)
        if (chunk_x, chunk_z) != (coord.x, coord.z):
            raise ValueError(f"Chunk coordinate mismatch in {path}")
        raw = memoryview(zlib.decompress(data[CHUNK_HEADER.size :]))
        chunk = Chunk(coord)
        offset = 0
        voxel_count = 16**3
        for section in chunk.sections:
            block_bytes = voxel_count * 2
            section.blocks[:] = np.frombuffer(raw[offset : offset + block_bytes], "<u2").reshape(
                section.blocks.shape
            )
            offset += block_bytes
            for target in (section.metadata, section.sky_light, section.block_light):
                target[:] = np.frombuffer(raw[offset : offset + voxel_count], np.uint8).reshape(
                    target.shape
                )
                offset += voxel_count
            section.dirty = DirtyFlag.MESH | DirtyFlag.LIGHTING
            section.revision = 1
        if offset != len(raw):
            raise ValueError(f"Unexpected chunk payload size in {path}")
        return chunk

    def save_player(self, snapshot: PlayerSnapshot) -> None:
        payload = {
            "version": SAVE_VERSION,
            "position": list(snapshot.position),
            "health": snapshot.health,
            "selected_slot": snapshot.selected_slot,
            "slots": [
                None if stack is None else {"item_id": stack.item_id, "count": stack.count}
                for stack in snapshot.slots
            ],
        }
        self.players.mkdir(parents=True, exist_ok=True)
        self._atomic_write_text(
            self.players / "local_player.json",
            json.dumps(payload, separators=(",", ":")),
        )

    def load_player(self, registry: ItemRegistry) -> PlayerSnapshot | None:
        path = self.players / "local_player.json"
        if not path.exists():
            return None
        payload = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
        version = payload.get("version")
        if version != SAVE_VERSION:
            raise ValueError(f"Unsupported player save version: {version}")
        raw_position = cast(list[float], payload["position"])
        raw_slots = cast(list[dict[str, int] | None], payload["slots"])
        slots: list[ItemStack | None] = []
        for raw in raw_slots:
            if raw is None:
                slots.append(None)
                continue
            stack = ItemStack(int(raw["item_id"]), int(raw["count"]))
            registry.by_id(stack.item_id)
            slots.append(stack)
        return PlayerSnapshot(
            (float(raw_position[0]), float(raw_position[1]), float(raw_position[2])),
            float(cast(float, payload["health"])),
            int(cast(int, payload["selected_slot"])),
            tuple(slots),
        )

    def restore_inventory(
        self,
        snapshot: PlayerSnapshot,
        inventory: Inventory,
        registry: ItemRegistry,
    ) -> None:
        if len(snapshot.slots) != len(inventory):
            raise ValueError("Player inventory dimensions changed")
        for index, stack in enumerate(snapshot.slots):
            inventory.set(index, stack, registry)

    def save_structure_world(self, world: StructureWorld) -> None:
        payload = {
            "version": SAVE_VERSION,
            "revision": world.revision,
            "structures": world.snapshots(),
        }
        self.structures.mkdir(parents=True, exist_ok=True)
        self._atomic_write_text(
            self.structures / "structures.json",
            json.dumps(payload, separators=(",", ":"), sort_keys=True),
        )

    def load_structure_world(self) -> StructureWorld:
        world = StructureWorld()
        path = self.structures / "structures.json"
        if not path.exists():
            return world
        payload = cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8")))
        if payload.get("version") != SAVE_VERSION:
            raise ValueError(f"Unsupported structure save version: {payload.get('version')}")
        raw_structures = payload.get("structures", [])
        if not isinstance(raw_structures, list):
            raise ValueError("Structure save must contain a structures array")
        snapshots: list[StructureSnapshot] = []
        for raw in cast("list[object]", raw_structures):
            if not isinstance(raw, dict):
                raise ValueError("Structure snapshots must be maps")
            snapshots.append(cast("StructureSnapshot", raw))
        try:
            world.replace_from_snapshots(snapshots)
        except (KeyError, TypeError, ValueError):
            return StructureWorld()
        saved_revision = payload.get("revision", world.revision)
        if isinstance(saved_revision, int):
            world.revision = max(world.revision, saved_revision)
        return world

    def _chunk_path(self, coord: ChunkCoord) -> Path:
        return self.regions / f"c.{coord.x}.{coord.z}.vchk"

    @staticmethod
    def _atomic_write_bytes(path: Path, data: bytes) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)

    @classmethod
    def _atomic_write_text(cls, path: Path, text: str) -> None:
        cls._atomic_write_bytes(path, text.encode("utf-8"))


def migrate_chunk(data: bytes, source_version: int, target_version: int) -> bytes:
    """Migration dispatch point for future save versions."""
    if source_version == target_version:
        return data
    raise ValueError(f"No chunk migration from version {source_version} to {target_version}")
