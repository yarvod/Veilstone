from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from voxel_sandbox.domain.inventory import Inventory
from voxel_sandbox.domain.items import ItemStack, create_core_item_registry
from voxel_sandbox.engine.chunks import Chunk, ChunkCoord, DirtyFlag
from voxel_sandbox.infrastructure.storage import (
    CHUNK_MAGIC,
    SAVE_VERSION,
    PlayerSnapshot,
    WorldStorage,
    migrate_chunk,
)


def test_world_metadata_and_compressed_chunk_roundtrip(tmp_path: Path) -> None:
    storage = WorldStorage(tmp_path / "world")
    metadata = storage.ensure_world(name="Test World", seed="stable-seed")
    chunk = Chunk(ChunkCoord(-2, 3))
    chunk.set_block(4, 20, 5, 10)
    chunk.set_metadata(4, 20, 5, 7)
    chunk.sections[1].sky_light[4, 4, 5] = 13

    storage.save_chunk(chunk)
    restored = storage.load_chunk(chunk.coord)

    assert metadata.version == SAVE_VERSION
    assert storage.load_metadata() == metadata
    assert (storage.regions / "c.-2.3.vchk").read_bytes().startswith(CHUNK_MAGIC)
    assert restored is not None
    for original, loaded in zip(chunk.sections, restored.sections, strict=True):
        assert np.array_equal(original.blocks, loaded.blocks)
        assert np.array_equal(original.metadata, loaded.metadata)
        assert np.array_equal(original.sky_light, loaded.sky_light)
        assert np.array_equal(original.block_light, loaded.block_light)
        assert not loaded.dirty & DirtyFlag.SAVE


def test_player_inventory_position_and_selection_roundtrip(tmp_path: Path) -> None:
    registry = create_core_item_registry()
    storage = WorldStorage(tmp_path / "world")
    storage.ensure_world(name="Test", seed="seed")
    inventory = Inventory()
    inventory.set(0, ItemStack(4, 12), registry)
    inventory.set(8, ItemStack(10, 1), registry)
    snapshot = PlayerSnapshot((1.5, 32.0, -4.5), 17.0, 8, tuple(inventory))

    storage.save_player(snapshot)
    restored = storage.load_player(registry)

    assert restored == snapshot
    empty = Inventory()
    assert restored is not None
    storage.restore_inventory(restored, empty, registry)
    assert tuple(empty) == snapshot.slots


def test_migration_stub_rejects_unknown_chunk_version() -> None:
    with pytest.raises(ValueError, match="No chunk migration"):
        migrate_chunk(b"old", 0, SAVE_VERSION)
