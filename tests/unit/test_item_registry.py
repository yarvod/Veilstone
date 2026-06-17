from __future__ import annotations

from pathlib import Path

import pytest

from voxel_sandbox.domain.items import (
    ItemDef,
    ItemRegistry,
    ItemStack,
    ItemType,
    create_core_item_registry,
    load_item_registry_from_toml,
)


def test_core_items_map_blocks_and_drops() -> None:
    registry = create_core_item_registry()

    assert registry.by_key("grass").block_id == 3
    assert registry.for_block(10) is not None
    assert registry.drop_for_block(6) == ItemStack(6, 1)
    assert registry.by_key("water_vessel").max_stack == 1


def test_item_registry_rejects_duplicate_ids_and_keys() -> None:
    first = ItemDef(1, "first", "First", ItemType.RESOURCE)

    with pytest.raises(ValueError, match="Duplicate item ID"):
        ItemRegistry((first, ItemDef(1, "second", "Second", ItemType.RESOURCE)))
    with pytest.raises(ValueError, match="Duplicate item key"):
        ItemRegistry((first, ItemDef(2, "first", "Other", ItemType.RESOURCE)))


_MINIMAL_ITEM_TOML = """\
[[item]]
id = 1
key = "stone"
name = "Stone"
item_type = "block"
block_id = 1

[[item]]
id = 6
key = "dusk_crystal"
name = "Dusk Crystal"
item_type = "resource"

[[item]]
id = 8
key = "water_vessel"
name = "Water Vessel"
item_type = "fluid_container"
max_stack = 1

[[drop]]
block_id = 1
item_id = 1
count = 1
"""


def test_load_item_registry_from_toml(tmp_path: Path) -> None:
    toml_file = tmp_path / "items.toml"
    toml_file.write_text(_MINIMAL_ITEM_TOML)

    registry = load_item_registry_from_toml(toml_file)

    assert len(registry) == 3
    assert registry.by_key("stone").block_id == 1
    assert registry.by_key("water_vessel").max_stack == 1
    assert registry.drop_for_block(1) == ItemStack(1, 1)
    assert registry.drop_for_block(99) is None


def test_load_item_registry_data_file() -> None:
    data_path = Path(__file__).parents[2] / "data" / "items.toml"
    registry = load_item_registry_from_toml(data_path)

    assert registry.by_key("grass").block_id == 3
    assert registry.by_key("water_vessel").max_stack == 1
    assert registry.drop_for_block(6) == ItemStack(6, 1)
    assert len(registry) == 10
