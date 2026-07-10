from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from voxel_sandbox.render.texture_atlas import GeneratedAtlas


class WorldTexturePackView(Protocol):
    def apply_texture_pack(self, atlas: GeneratedAtlas) -> None: ...


class InventoryTexturePackView(Protocol):
    def refresh_item_icons(self, atlas: GeneratedAtlas) -> None: ...


@dataclass(frozen=True, slots=True)
class ResourcePackPresentationAdapter:
    world: WorldTexturePackView
    inventory: InventoryTexturePackView

    def apply_texture_pack(self, atlas: GeneratedAtlas) -> None:
        """Apply one loaded atlas to both world and existing inventory sprites."""

        self.world.apply_texture_pack(atlas)
        self.inventory.refresh_item_icons(atlas)
