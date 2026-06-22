from __future__ import annotations

from pathlib import Path

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
