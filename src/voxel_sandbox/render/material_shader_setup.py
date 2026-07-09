from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from voxel_sandbox.render.material_binding import (
    MaterialAtlasBindingPlan,
    build_material_atlas_binding_plan,
)
from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.material_quality import (
    ChunkShaderVariant,
    MaterialPipelineDecision,
    resolve_chunk_shader_variant,
)


@dataclass(frozen=True, slots=True)
class MaterialShaderSetup:
    shader: ChunkShaderVariant
    binding_plan: MaterialAtlasBindingPlan

    @property
    def uses_material_shader(self) -> bool:
        return self.shader.requires_material_atlases


def build_material_shader_setup(
    decision: MaterialPipelineDecision,
    available_roles: Iterable[MaterialMapRole] = (),
    *,
    # Units 0 (color atlas) and 1 (shadow map) are reserved by the chunk pipeline.
    first_texture_unit: int = 2,
) -> MaterialShaderSetup:
    shader = resolve_chunk_shader_variant(decision)
    binding_plan = build_material_atlas_binding_plan(
        decision,
        available_roles,
        first_texture_unit=first_texture_unit,
    )
    return MaterialShaderSetup(shader=shader, binding_plan=binding_plan)
