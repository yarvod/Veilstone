from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import moderngl

from voxel_sandbox.render.material_binding import MaterialAtlasBinding
from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.material_shader_runtime import MaterialShaderActivation
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


def build_activated_material_atlas_textures(
    context: Any,
    activation: MaterialShaderActivation | None,
    bundle: GeneratedMaterialAtlasBundle | None,
) -> dict[MaterialMapRole, MaterialAtlasTexture]:
    if activation is None:
        return {}
    return build_material_atlas_textures(context, bundle, activation.material_bindings)


def bind_material_atlas_textures(
    textures: dict[MaterialMapRole, MaterialAtlasTexture],
) -> tuple[int, ...]:
    bound_units: list[int] = []
    for material_texture in textures.values():
        material_texture.texture.use(material_texture.texture_unit)
        bound_units.append(material_texture.texture_unit)
    return tuple(bound_units)


def release_material_atlas_textures(
    textures: dict[MaterialMapRole, MaterialAtlasTexture],
) -> None:
    for material_texture in textures.values():
        material_texture.texture.release()
