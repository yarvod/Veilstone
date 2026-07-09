from __future__ import annotations

from pathlib import Path
from typing import cast

from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.material_quality import resolve_material_pipeline
from voxel_sandbox.render.material_shader_runtime import (
    MaterialShaderActivation,
    activate_material_shader,
    apply_material_sampler_bindings,
    build_material_shader_runtime_wiring,
    resolve_chunk_draw_shader,
)
from voxel_sandbox.render.material_shader_setup import build_material_shader_setup
from voxel_sandbox.render.shaders.loader import ShaderProgram


class _FakeUniform:
    def __init__(self) -> None:
        self.value: int | None = None


class _FakeProgram:
    def __init__(self) -> None:
        self.released = False
        self.uniforms: dict[str, _FakeUniform] = {}

    def release(self) -> None:
        self.released = True

    def __getitem__(self, name: str) -> _FakeUniform:
        return self.uniforms.setdefault(name, _FakeUniform())


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
    assert apply_material_sampler_bindings(None) == ()


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


def test_material_preview_sampler_bindings_write_planned_units(tmp_path: Path) -> None:
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
        (MaterialMapRole.NORMAL, MaterialMapRole.SPECULAR),
        first_texture_unit=4,
    )
    wiring = build_material_shader_runtime_wiring(setup, shader_root)
    context = _FakeContext()
    activation = activate_material_shader(context, wiring)

    applied = apply_material_sampler_bindings(activation)

    assert activation is not None
    assert applied == activation.material_bindings
    program = activation.shader.program
    assert isinstance(program, _FakeProgram)
    assert program.uniforms["u_material_normal_atlas"].value == 4
    assert program.uniforms["u_material_specular_atlas"].value == 5
    assert program.uniforms["u_material_has_normal"].value == 1
    assert program.uniforms["u_material_has_specular"].value == 1
    assert "u_material_emissive_atlas" not in program.uniforms
    assert "u_material_has_emissive" not in program.uniforms
    assert "u_material_has_mer" not in program.uniforms


def test_chunk_draw_shader_defaults_without_activation() -> None:
    default_shader = cast(ShaderProgram, object())

    assert resolve_chunk_draw_shader(default_shader, None) is default_shader


def test_chunk_draw_shader_uses_activated_material_shader() -> None:
    default_shader = cast(ShaderProgram, object())
    activation_shader = cast(ShaderProgram, object())
    activation = MaterialShaderActivation(
        shader=activation_shader,
        material_bindings=(),
    )

    assert resolve_chunk_draw_shader(default_shader, activation) is activation_shader
