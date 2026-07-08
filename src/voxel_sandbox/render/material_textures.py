from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import moderngl

from voxel_sandbox.render.material_binding import MaterialAtlasBinding
from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.texture_atlas import GeneratedMaterialAtlasBundle


@dataclass(frozen=True, slots=True)
class MaterialAtlasTexture:
    role: MaterialMapRole
    texture_unit: int
    texture: Any


def build_material_atlas_textures(
    context: Any,
    bundle: GeneratedMaterialAtlasBundle | None,
    bindings: tuple[MaterialAtlasBinding, ...],
) -> dict[MaterialMapRole, MaterialAtlasTexture]:
    if bundle is None:
        return {}
    textures: dict[MaterialMapRole, MaterialAtlasTexture] = {}
    for binding in bindings:
        atlas = bundle.materials.get(binding.role)
        if atlas is None:
            continue
        texture = context.texture((atlas.width, atlas.height), 4, atlas.pixels)
        texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        texture.repeat_x = False
        texture.repeat_y = False
        textures[binding.role] = MaterialAtlasTexture(
            role=binding.role,
            texture_unit=binding.texture_unit,
            texture=texture,
        )
    return textures
