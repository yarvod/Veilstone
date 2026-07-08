from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.material_quality import (
    MaterialPipelineDecision,
    resolve_chunk_shader_variant,
)


@dataclass(frozen=True, slots=True)
class MaterialAtlasBinding:
    role: MaterialMapRole
    sampler_name: str
    texture_unit: int


@dataclass(frozen=True, slots=True)
class MaterialAtlasBindingPlan:
    bindings: tuple[MaterialAtlasBinding, ...] = ()

    @property
    def enabled(self) -> bool:
        return bool(self.bindings)


_SAMPLER_NAMES: dict[MaterialMapRole, str] = {
    MaterialMapRole.NORMAL: "u_material_normal_atlas",
    MaterialMapRole.SPECULAR: "u_material_specular_atlas",
    MaterialMapRole.EMISSIVE: "u_material_emissive_atlas",
    MaterialMapRole.MER: "u_material_mer_atlas",
}


def build_material_atlas_binding_plan(
    decision: MaterialPipelineDecision,
    available_roles: Iterable[MaterialMapRole],
    *,
    first_texture_unit: int = 1,
) -> MaterialAtlasBindingPlan:
    variant = resolve_chunk_shader_variant(decision)
    if not variant.requires_material_atlases:
        return MaterialAtlasBindingPlan()

    bindings = tuple(
        MaterialAtlasBinding(
            role=role,
            sampler_name=_SAMPLER_NAMES[role],
            texture_unit=first_texture_unit + index,
        )
        for index, role in enumerate(sorted(set(available_roles), key=lambda role: role.value))
        if role in _SAMPLER_NAMES
    )
    return MaterialAtlasBindingPlan(bindings=bindings)
