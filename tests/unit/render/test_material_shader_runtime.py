from __future__ import annotations

from pathlib import Path

from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.material_quality import resolve_material_pipeline
from voxel_sandbox.render.material_shader_runtime import (
    build_material_shader_runtime_wiring,
)
from voxel_sandbox.render.material_shader_setup import build_material_shader_setup


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
