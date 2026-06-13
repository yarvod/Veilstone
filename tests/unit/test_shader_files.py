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
