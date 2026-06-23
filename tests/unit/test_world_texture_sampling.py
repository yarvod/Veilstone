from __future__ import annotations

from pathlib import Path


def test_world_block_atlas_uses_pixel_sampling_without_mip_bleed() -> None:
    source = (Path(__file__).parents[2] / "src/voxel_sandbox/render/world_scene.py").read_text(
        encoding="utf-8"
    )

    assert "texture.filter = (moderngl.NEAREST, moderngl.NEAREST)" in source
    assert "texture.repeat_x = False" in source
    assert "texture.repeat_y = False" in source
    assert ".build_mipmaps()" not in source


def test_shadow_depth_mesh_receives_atlas_cutout_attributes() -> None:
    source = (Path(__file__).parents[2] / "src/voxel_sandbox/render/meshes/gpu_cache.py").read_text(
        encoding="utf-8"
    )

    assert '"3f 2f 24x 4f"' in source
    assert '"in_uv"' in source
    assert '"in_atlas_rect"' in source
