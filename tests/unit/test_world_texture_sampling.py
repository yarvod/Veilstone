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

    assert '"3f 2f 24x 4f 1f"' in source
    assert '"in_uv"' in source
    assert '"in_atlas_rect"' in source
    assert '"in_wind_motion"' in source


def test_water_mesh_cache_skips_wind_motion_attribute_binding() -> None:
    cache_source = (
        Path(__file__).parents[2] / "src/voxel_sandbox/render/meshes/gpu_cache.py"
    ).read_text(encoding="utf-8")
    scene_source = (
        Path(__file__).parents[2] / "src/voxel_sandbox/render/world_scene.py"
    ).read_text(encoding="utf-8")

    assert "wind_motion: bool = True" in cache_source
    assert '"3f 2f 3f 1f 1f 1f 4f"' in cache_source
    assert '"3f 2f 24x 4f"' in cache_source
    assert "wind_motion=False" in scene_source


def test_material_quality_setting_reaches_world_renderer_decision() -> None:
    scene_source = (
        Path(__file__).parents[2] / "src/voxel_sandbox/render/world_scene.py"
    ).read_text(encoding="utf-8")
    window_source = (Path(__file__).parents[2] / "src/voxel_sandbox/render/window.py").read_text(
        encoding="utf-8"
    )

    assert "resolve_material_pipeline_from_graphics" in scene_source
    assert "self.material_pipeline" in scene_source
    assert "material_quality=settings.graphics.material_quality" in window_source


def test_shadow_depth_pass_renders_cutout_and_entity_faces_without_culling() -> None:
    source = (Path(__file__).parents[2] / "src/voxel_sandbox/render/world_scene.py").read_text(
        encoding="utf-8"
    )
    shadow_pass = source[source.index("def _render_shadow_depth") :]

    assert "self.context.disable(moderngl.CULL_FACE)" in shadow_pass
    assert 'self.context.cull_face = "front"' not in shadow_pass
