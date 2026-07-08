from __future__ import annotations

from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.material_quality import resolve_material_pipeline
from voxel_sandbox.render.material_shader_setup import build_material_shader_setup


def test_default_material_shader_setup_skips_material_work() -> None:
    setup = build_material_shader_setup(
        resolve_material_pipeline("color-only"),
        (MaterialMapRole.NORMAL,),
    )

    assert setup.shader.shader_name == "chunk_opaque"
    assert setup.uses_material_shader is False
    assert setup.binding_plan.enabled is False
    assert setup.binding_plan.bindings == ()


def test_low_material_shader_setup_skips_material_work() -> None:
    setup = build_material_shader_setup(
        resolve_material_pipeline("low"),
        (MaterialMapRole.NORMAL, MaterialMapRole.SPECULAR),
    )

    assert setup.shader.shader_name == "chunk_opaque"
    assert setup.uses_material_shader is False
    assert setup.binding_plan.enabled is False


def test_material_preview_shader_setup_consumes_binding_plan() -> None:
    setup = build_material_shader_setup(
        resolve_material_pipeline("material-preview"),
        (MaterialMapRole.EMISSIVE, MaterialMapRole.NORMAL),
        first_texture_unit=2,
    )

    assert setup.shader.shader_name == "chunk_material_preview"
    assert setup.uses_material_shader is True
    assert setup.binding_plan.enabled is True
    assert tuple(binding.role for binding in setup.binding_plan.bindings) == (
        MaterialMapRole.EMISSIVE,
        MaterialMapRole.NORMAL,
    )
    assert tuple(binding.texture_unit for binding in setup.binding_plan.bindings) == (2, 3)
