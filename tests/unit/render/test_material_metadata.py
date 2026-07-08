from __future__ import annotations

from voxel_sandbox.render.material_metadata import (
    MaterialMapRole,
    MaterialTextureRef,
    RenderMaterialMetadata,
    material_sidecar_refs,
)


def test_color_only_material_cache_key_uses_resource_and_color_asset() -> None:
    metadata = RenderMaterialMetadata(
        resource_id="minecraft:block/stone",
        color_asset_path="assets/minecraft/textures/block/stone.png",
    )

    assert metadata.cache_key().resource_id == "minecraft:block/stone"
    assert metadata.cache_key().color_asset_path == "assets/minecraft/textures/block/stone.png"
    assert metadata.cache_key().shader_profile == "color"
    assert metadata.cache_key().maps == ()


def test_material_cache_key_orders_maps_by_role_and_asset_path() -> None:
    metadata = RenderMaterialMetadata(
        resource_id="minecraft:block/lantern",
        color_asset_path="assets/minecraft/textures/block/lantern.png",
        maps=(
            MaterialTextureRef(
                MaterialMapRole.SPECULAR,
                "assets/minecraft/textures/block/lantern_s.png",
            ),
            MaterialTextureRef(
                MaterialMapRole.NORMAL,
                "assets/minecraft/textures/block/lantern_n.png",
            ),
        ),
        shader_profile="pbr",
    )

    assert metadata.cache_key().maps == (
        ("normal", "assets/minecraft/textures/block/lantern_n.png"),
        ("specular", "assets/minecraft/textures/block/lantern_s.png"),
    )


def test_material_sidecar_refs_match_common_java_pack_suffixes() -> None:
    refs = material_sidecar_refs("assets/minecraft/textures/block/stone.png")

    assert tuple((ref.role, ref.asset_path) for ref in refs) == (
        (MaterialMapRole.NORMAL, "assets/minecraft/textures/block/stone_n.png"),
        (MaterialMapRole.SPECULAR, "assets/minecraft/textures/block/stone_s.png"),
        (MaterialMapRole.EMISSIVE, "assets/minecraft/textures/block/stone_e.png"),
        (MaterialMapRole.MER, "assets/minecraft/textures/block/stone_mer.png"),
    )
