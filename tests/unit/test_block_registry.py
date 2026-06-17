from __future__ import annotations

from pathlib import Path

import pytest

from voxel_sandbox.domain.blocks import (
    BlockDef,
    BlockRegistry,
    Material,
    create_core_block_registry,
    load_block_registry_from_toml,
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
    assert len(registry) == 13


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


_MINIMAL_TOML = """\
[[block]]
id = 0
key = "air"
name = "Air"
material = "air"
hardness = 0.0
is_solid = false
is_opaque = false
is_transparent = true

[[block]]
id = 1
key = "stone"
name = "Stone"
material = "stone"
hardness = 1.5
texture_top = "stone"
texture_side = "stone"
texture_bottom = "stone"

[[block]]
id = 7
key = "gloam_lantern"
name = "Gloam Lantern"
material = "light"
hardness = 0.1
is_solid = false
is_opaque = false
is_transparent = true
emits_light = 14
texture_top = "gloam_lantern"
texture_side = "gloam_lantern"
texture_bottom = "gloam_lantern"
"""


def test_load_block_registry_from_toml(tmp_path: Path) -> None:
    toml_file = tmp_path / "blocks.toml"
    toml_file.write_text(_MINIMAL_TOML)

    registry = load_block_registry_from_toml(toml_file)

    assert len(registry) == 3
    assert registry.by_id(0).key == "air"
    assert not registry.by_id(0).is_solid
    assert registry.by_key("stone").material is Material.STONE
    assert registry.by_key("gloam_lantern").emits_light == 14
    assert registry.by_key("gloam_lantern").is_transparent


def test_load_block_registry_auto_id(tmp_path: Path) -> None:
    toml_file = tmp_path / "blocks.toml"
    toml_file.write_text(
        "[[block]]\nkey='air'\nname='Air'\nmaterial='air'\nhardness=0.0\n"
        "is_solid=false\nis_opaque=false\nis_transparent=true\n\n"
        "[[block]]\nkey='stone'\nname='Stone'\nmaterial='stone'\nhardness=1.5\n"
    )
    registry = load_block_registry_from_toml(toml_file)

    assert registry.by_id(0).key == "air"
    assert registry.by_id(1).key == "stone"


def test_load_block_registry_data_file() -> None:
    data_path = Path(__file__).parents[2] / "data" / "blocks.toml"
    registry = load_block_registry_from_toml(data_path)

    assert registry.by_id(0).key == "air"
    assert registry.by_key("water").is_fluid
    assert len(registry) == 13
