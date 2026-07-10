from __future__ import annotations

from pathlib import Path

from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.material_quality import resolve_material_pipeline
from voxel_sandbox.render.material_shader_runtime import build_material_shader_runtime_wiring
from voxel_sandbox.render.material_shader_setup import build_material_shader_setup
from voxel_sandbox.render.shaders.loader import ShaderFiles


def test_shader_files_read_sources_and_signature(tmp_path: Path) -> None:
    vertex = tmp_path / "test.vert"
    fragment = tmp_path / "test.frag"
    vertex.write_text("vertex source", encoding="utf-8")
    fragment.write_text("fragment source", encoding="utf-8")
    files = ShaderFiles.from_directory(tmp_path, "test")

    assert files.read() == ("vertex source", "fragment source")
    vertex_time, fragment_time = files.signature()
    assert vertex_time > 0
    assert fragment_time > 0


def test_material_preview_shader_fixture_matches_runtime_wiring_names() -> None:
    shader_root = Path(__file__).parents[2] / "src/voxel_sandbox/render/shaders/glsl"
    setup = build_material_shader_setup(
        resolve_material_pipeline("material-preview"),
        (MaterialMapRole.NORMAL, MaterialMapRole.SPECULAR),
    )
    wiring = build_material_shader_runtime_wiring(setup, shader_root)

    assert wiring.material_shader_files is not None
    assert wiring.material_shader_files.vertex == shader_root / "chunk_material_preview.vert"
    assert wiring.material_shader_files.fragment == shader_root / "chunk_material_preview.frag"
    vertex_source, fragment_source = wiring.material_shader_files.read()
    assert "in vec3 in_position;" in vertex_source
    assert "in vec4 in_atlas_rect;" in vertex_source
    for binding in wiring.material_bindings:
        assert f"uniform sampler2D {binding.sampler_name};" in fragment_source

    chunk_opaque_fragment = (shader_root / "chunk_opaque.frag").read_text(encoding="utf-8")
    assert "u_material_normal_atlas" not in chunk_opaque_fragment


def test_entity_and_shadow_shaders_rotate_local_front_toward_positive_yaw() -> None:
    shader_root = Path(__file__).parents[2] / "src/voxel_sandbox/render/shaders/glsl"
    entity_vertex = (shader_root / "entity.vert").read_text(encoding="utf-8")
    shadow_vertex = (shader_root / "entity_shadow_depth.vert").read_text(encoding="utf-8")
    yaw_matrix = "cos(entity_yaw), sin(entity_yaw),"
    inverse_column = "-sin(entity_yaw), cos(entity_yaw)"

    assert yaw_matrix in entity_vertex
    assert inverse_column in entity_vertex
    assert yaw_matrix in shadow_vertex
    assert inverse_column in shadow_vertex


def test_chunk_shader_discards_cutout_alpha() -> None:
    shader_root = Path(__file__).parents[2] / "src/voxel_sandbox/render/shaders/glsl"
    fragment = (shader_root / "chunk_opaque.frag").read_text(encoding="utf-8")

    assert "base_color.a < 0.5" in fragment
    assert "discard;" in fragment


def test_chunk_and_shadow_shaders_clamp_atlas_tile_uvs() -> None:
    shader_root = Path(__file__).parents[2] / "src/voxel_sandbox/render/shaders/glsl"
    chunk_fragment = (shader_root / "chunk_opaque.frag").read_text(encoding="utf-8")
    shadow_fragment = (shader_root / "shadow_depth.frag").read_text(encoding="utf-8")

    for source in (chunk_fragment, shadow_fragment):
        assert "uniform float tile_uv_margin;" in source
        assert "clamp(" in source
        assert "vec2(tile_uv_margin)" in source
        assert "vec2(1.0 - tile_uv_margin)" in source


def test_chunk_and_shadow_vertex_shaders_apply_vegetation_wind() -> None:
    shader_root = Path(__file__).parents[2] / "src/voxel_sandbox/render/shaders/glsl"
    chunk_vertex = (shader_root / "chunk_opaque.vert").read_text(encoding="utf-8")
    shadow_vertex = (shader_root / "shadow_depth.vert").read_text(encoding="utf-8")

    for source in (chunk_vertex, shadow_vertex):
        assert "uniform float vegetation_wind_time;" in source
        assert "uniform int vegetation_wind_enabled;" in source
        assert "in float in_wind_motion;" in source
        assert "apply_vegetation_wind" in source
        assert "vegetation_wind_enabled == 0" in source
        assert "in_wind_motion > 1.5" in source


def test_chunk_shader_uses_soft_terrain_shadow_filter() -> None:
    shader_root = Path(__file__).parents[2] / "src/voxel_sandbox/render/shaders/glsl"
    fragment = (shader_root / "chunk_opaque.frag").read_text(encoding="utf-8")

    assert "filtered_visibility" in fragment
    assert "for (int x = -2; x <= 2; ++x)" in fragment
    assert "for (int y = -2; y <= 2; ++y)" in fragment
    assert "float filtered_visibility = visibility / 25.0;" in fragment
    assert "return filtered_visibility;" in fragment
    assert "max(shadow_bias, 0.004)" not in fragment


def test_chunk_shader_does_not_flip_cutout_tiles_randomly() -> None:
    shader_root = Path(__file__).parents[2] / "src/voxel_sandbox/render/shaders/glsl"
    fragment = (shader_root / "chunk_opaque.frag").read_text(encoding="utf-8")

    assert "tile_uv.x = 1.0 - tile_uv.x" not in fragment
    assert "tile_uv.y = 1.0 - tile_uv.y" not in fragment


def test_shadow_depth_shader_discards_cutout_alpha() -> None:
    shader_root = Path(__file__).parents[2] / "src/voxel_sandbox/render/shaders/glsl"
    vertex = (shader_root / "shadow_depth.vert").read_text(encoding="utf-8")
    fragment = (shader_root / "shadow_depth.frag").read_text(encoding="utf-8")

    assert "in vec2 in_uv" in vertex
    assert "in vec4 in_atlas_rect" in vertex
    assert "uniform sampler2D texture_atlas" in fragment
    assert "texture(texture_atlas, atlas_uv).a < 0.5" in fragment
    assert "discard;" in fragment


def test_chunk_shader_keeps_world_shadows_readable() -> None:
    shader_root = Path(__file__).parents[2] / "src/voxel_sandbox/render/shaders/glsl"
    fragment = (shader_root / "chunk_opaque.frag").read_text(encoding="utf-8")

    assert "max(shadow_bias, 0.0015)" in fragment
    assert "float shadow = mix(0.48, 1.0, sample_shadow())" in fragment
    assert "float ambient_sky = sky * 0.36" in fragment


def test_water_shader_adds_surface_crest_highlights() -> None:
    shader_root = Path(__file__).parents[2] / "src/voxel_sandbox/render/shaders/glsl"
    fragment = (shader_root / "water.frag").read_text(encoding="utf-8")

    assert "crest_wave" in fragment
    assert "uniform int water_detail_enabled;" in fragment
    assert "crest *= water_detail;" in fragment
    assert "highlight_color" in fragment
    assert "lit_color += highlight_color * crest" in fragment
    assert "0.44 + fresnel * 0.24 + crest * 0.05" in fragment


def test_water_shader_uses_detail_gated_ripple_normals_for_reflections() -> None:
    shader_root = Path(__file__).parents[2] / "src/voxel_sandbox/render/shaders/glsl"
    fragment = (shader_root / "water.frag").read_text(encoding="utf-8")

    assert "float water_detail = float(water_detail_enabled);" in fragment
    assert "ripple_x" in fragment
    assert "ripple_z" in fragment
    assert "vec3 ripple_normal" in fragment
    assert "surface * water_detail" in fragment
    assert "dot(water_normal, view_direction)" in fragment
    assert "float reflection_strength" in fragment
