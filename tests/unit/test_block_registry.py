from __future__ import annotations

import pytest

from voxel_sandbox.domain.blocks import (
    BlockDef,
    BlockRegistry,
    Material,
    create_core_block_registry,
)


def block(block_id: int, key: str) -> BlockDef:
    return BlockDef(block_id, key, key.title(), Material.STONE, hardness=1.0)


def test_core_registry_reserves_zero_for_air() -> None:
    registry = create_core_block_registry()

    assert registry.by_id(0).key == "air"
    assert registry.by_key("grass").id == 3
    assert registry.by_key("veilwood_log").id == 4
    assert registry.by_key("dusk_crystal_ore").id == 6
    assert registry.by_key("gloam_lantern").emits_light == 14
    assert registry.by_key("water").is_fluid
    assert not registry.by_key("water").is_solid
    assert registry.by_key("workbench").id == 10
    assert len(registry) == 11


def test_registry_rejects_duplicate_ids_and_keys() -> None:
    air = BlockDef(0, "air", "Air", Material.AIR, 0.0, is_solid=False, is_opaque=False)

    with pytest.raises(ValueError, match="Duplicate block ID"):
        BlockRegistry((air, block(1, "first"), block(1, "second")))
    with pytest.raises(ValueError, match="Duplicate block key"):
        BlockRegistry((air, block(1, "same"), block(2, "same")))


def test_registry_requires_air_at_zero() -> None:
    with pytest.raises(ValueError, match="ID 0"):
        BlockRegistry((block(1, "stone"),))


def test_block_definition_validates_storage_limits() -> None:
    with pytest.raises(ValueError, match="uint16"):
        block(65536, "overflow")
