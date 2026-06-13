from __future__ import annotations

import pytest

from voxel_sandbox.domain.items import (
    ItemDef,
    ItemRegistry,
    ItemStack,
    ItemType,
    create_core_item_registry,
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
