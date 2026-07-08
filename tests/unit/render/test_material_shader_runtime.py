from __future__ import annotations

from pathlib import Path

from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.material_quality import resolve_material_pipeline
from voxel_sandbox.render.material_shader_runtime import (
    activate_material_shader,
    build_material_shader_runtime_wiring,
)
from voxel_sandbox.render.material_shader_setup import build_material_shader_setup


class _FakeProgram:
    def __init__(self) -> None:
        self.released = False

    def release(self) -> None:
        self.released = True


class _FakeContext:
    def __init__(self) -> None:
        self.vertex_source = ""
        self.fragment_source = ""

    def program(self, *, vertex_shader: str, fragment_shader: str) -> _FakeProgram:
        self.vertex_source = vertex_shader
        self.fragment_source = fragment_shader
        return _FakeProgram()


def test_default_runtime_wiring_does_not_name_material_shader_files() -> None:
    setup = build_material_shader_setup(
        resolve_material_pipeline("color-only"),
        (MaterialMapRole.NORMAL,),
    )

    wiring = build_material_shader_runtime_wiring(setup, Path("shaders/glsl"))

    assert wiring.chunk_shader_name == "chunk_opaque"
    assert wiring.uses_material_shader is False
    assert wiring.material_shader_files is None
    assert wiring.material_bindings == ()


def test_default_runtime_activation_is_skipped() -> None:
    setup = build_material_shader_setup(resolve_material_pipeline("color-only"))
    wiring = build_material_shader_runtime_wiring(setup, Path("shaders/glsl"))

    assert activate_material_shader(_FakeContext(), wiring) is None


def test_material_preview_runtime_wiring_names_shader_files_and_bindings() -> None:
    setup = build_material_shader_setup(
        resolve_material_pipeline("material-preview"),
        (MaterialMapRole.SPECULAR,),
        first_texture_unit=5,
    )

    wiring = build_material_shader_runtime_wiring(setup, Path("shaders/glsl"))

    assert wiring.chunk_shader_name == "chunk_material_preview"
    assert wiring.uses_material_shader is True
    assert wiring.material_shader_files is not None
    assert wiring.material_shader_files.vertex.as_posix().endswith(
        "shaders/glsl/chunk_material_preview.vert"
    )
    assert wiring.material_shader_files.fragment.as_posix().endswith(
        "shaders/glsl/chunk_material_preview.frag"
    )
    assert tuple(binding.role for binding in wiring.material_bindings) == (
        MaterialMapRole.SPECULAR,
    )
    assert tuple(binding.texture_unit for binding in wiring.material_bindings) == (5,)


def test_material_preview_runtime_activation_uses_shader_files_and_bindings(
    tmp_path: Path,
) -> None:
    shader_root = tmp_path / "shaders"
    shader_root.mkdir()
    (shader_root / "chunk_material_preview.vert").write_text(
        "#version 330 core\nvoid main() { gl_Position = vec4(0.0); }\n",
        encoding="utf-8",
    )
    (shader_root / "chunk_material_preview.frag").write_text(
        "#version 330 core\nout vec4 frag_color; void main() { frag_color = vec4(1.0); }\n",
        encoding="utf-8",
    )
    setup = build_material_shader_setup(
        resolve_material_pipeline("material-preview"),
        (MaterialMapRole.NORMAL,),
        first_texture_unit=7,
    )
    wiring = build_material_shader_runtime_wiring(setup, shader_root)
    context = _FakeContext()

    activation = activate_material_shader(context, wiring)

    assert activation is not None
    assert "gl_Position" in context.vertex_source
    assert "frag_color" in context.fragment_source
    assert tuple(binding.role for binding in activation.material_bindings) == (
        MaterialMapRole.NORMAL,
    )
    assert tuple(binding.texture_unit for binding in activation.material_bindings) == (7,)
