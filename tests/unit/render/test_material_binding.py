from __future__ import annotations

from voxel_sandbox.render.material_binding import build_material_atlas_binding_plan
from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.material_quality import resolve_material_pipeline


def test_color_only_material_binding_plan_is_empty() -> None:
    plan = build_material_atlas_binding_plan(
        resolve_material_pipeline("color-only"),
        (MaterialMapRole.NORMAL, MaterialMapRole.SPECULAR),
    )

    assert plan.enabled is False
    assert plan.bindings == ()


def test_low_material_binding_plan_is_empty_even_when_roles_exist() -> None:
    plan = build_material_atlas_binding_plan(
        resolve_material_pipeline("low"),
        (MaterialMapRole.NORMAL,),
    )

    assert plan.enabled is False
    assert plan.bindings == ()


def test_material_preview_binding_plan_default_units_avoid_reserved_slots() -> None:
    plan = build_material_atlas_binding_plan(
        resolve_material_pipeline("material-preview"),
        (MaterialMapRole.NORMAL, MaterialMapRole.SPECULAR),
    )

    # Units 0 (color atlas) and 1 (shadow map) are reserved by the chunk pipeline.
    assert tuple(binding.texture_unit for binding in plan.bindings) == (2, 3)


def test_material_preview_binding_plan_names_available_roles() -> None:
    plan = build_material_atlas_binding_plan(
        resolve_material_pipeline("material-preview"),
        (
            MaterialMapRole.SPECULAR,
            MaterialMapRole.NORMAL,
            MaterialMapRole.NORMAL,
        ),
        first_texture_unit=3,
    )

    assert plan.enabled is True
    assert tuple(binding.role for binding in plan.bindings) == (
        MaterialMapRole.NORMAL,
        MaterialMapRole.SPECULAR,
    )
    assert tuple(binding.sampler_name for binding in plan.bindings) == (
        "u_material_normal_atlas",
        "u_material_specular_atlas",
    )
    assert tuple(binding.texture_unit for binding in plan.bindings) == (3, 4)
