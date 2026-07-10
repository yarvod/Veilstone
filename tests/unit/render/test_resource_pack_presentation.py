from __future__ import annotations

from voxel_sandbox.render.resource_pack_presentation import ResourcePackPresentationAdapter
from voxel_sandbox.render.texture_atlas import GeneratedAtlas


def test_resource_pack_presentation_refreshes_world_and_existing_inventory_icons() -> None:
    calls: list[tuple[str, GeneratedAtlas]] = []

    class World:
        def apply_texture_pack(self, atlas: GeneratedAtlas) -> None:
            calls.append(("world", atlas))

    class Inventory:
        def refresh_item_icons(self, atlas: GeneratedAtlas) -> None:
            calls.append(("inventory", atlas))

    atlas = GeneratedAtlas(1, 1, b"\x00\x00\x00\xff", {})

    ResourcePackPresentationAdapter(World(), Inventory()).apply_texture_pack(atlas)

    assert calls == [("world", atlas), ("inventory", atlas)]
