from __future__ import annotations

from dataclasses import dataclass

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.domain.items import ItemRegistry

type TextureRect = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class BlockModelSnapshot:
    block_id: int
    key: str
    name: str
    texture_top: str
    texture_side: str
    texture_bottom: str
    render_layer: str
    render_shape: str

    def texture_for_face(self, face: str) -> str:
        if face == "side":
            return self.texture_side
        if face == "bottom":
            return self.texture_bottom
        return self.texture_top


@dataclass(frozen=True, slots=True)
class ItemModelSnapshot:
    item_id: int
    key: str
    name: str
    item_type: str
    block: BlockModelSnapshot | None = None

    @property
    def is_block(self) -> bool:
        return self.block is not None


def build_block_model_snapshot(
    block_id: int,
    block_registry: BlockRegistry,
) -> BlockModelSnapshot:
    block = block_registry.by_id(block_id)
    return BlockModelSnapshot(
        block_id=block.id,
        key=block.key,
        name=block.name,
        texture_top=block.texture_top,
        texture_side=block.texture_side,
        texture_bottom=block.texture_bottom,
        render_layer=block.render_layer,
        render_shape=block.render_shape,
    )


def build_item_model_snapshot(
    item_id: int,
    item_registry: ItemRegistry,
    block_registry: BlockRegistry,
) -> ItemModelSnapshot:
    item = item_registry.by_id(item_id)
    block = (
        build_block_model_snapshot(item.block_id, block_registry)
        if item.block_id is not None
        else None
    )
    return ItemModelSnapshot(
        item_id=item.id,
        key=item.key,
        name=item.name,
        item_type=item.item_type.value,
        block=block,
    )


def build_item_block_model_snapshot(
    item_id: int,
    item_registry: ItemRegistry,
    block_registry: BlockRegistry,
) -> BlockModelSnapshot | None:
    return build_item_model_snapshot(item_id, item_registry, block_registry).block


def item_block_texture_name(
    item_id: int,
    item_registry: ItemRegistry,
    block_registry: BlockRegistry,
    *,
    face: str = "top",
) -> str | None:
    block = build_item_block_model_snapshot(item_id, item_registry, block_registry)
    if block is None:
        return None
    return block.texture_for_face(face)


def item_block_atlas_rect(
    item_id: int,
    item_registry: ItemRegistry,
    block_registry: BlockRegistry,
    atlas_uvs: dict[str, TextureRect],
    *,
    face: str = "top",
) -> TextureRect | None:
    texture_name = item_block_texture_name(
        item_id,
        item_registry,
        block_registry,
        face=face,
    )
    if texture_name is None:
        return None
    return atlas_uvs.get(texture_name)
