from __future__ import annotations

from typing import cast

import moderngl

from voxel_sandbox.render.material_binding import MaterialAtlasBinding
from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.material_shader_runtime import MaterialShaderActivation
from voxel_sandbox.render.material_textures import (
    bind_material_atlas_textures,
    build_activated_material_atlas_textures,
    build_material_atlas_textures,
    release_material_atlas_textures,
)
from voxel_sandbox.render.shaders.loader import ShaderProgram
from voxel_sandbox.render.texture_atlas import (
    GeneratedAtlas,
    GeneratedMaterialAtlas,
    GeneratedMaterialAtlasBundle,
)


class _FakeTexture:
    def __init__(self, size: tuple[int, int], components: int, pixels: bytes) -> None:
        self.size = size
        self.components = components
        self.pixels = pixels
        self.filter: tuple[int, int] | None = None
        self.repeat_x = True
        self.repeat_y = True
        self.released = False
        self.used_units: list[int] = []

    def release(self) -> None:
        self.released = True

    def use(self, location: int) -> None:
        self.used_units.append(location)


class _FakeContext:
    def __init__(self) -> None:
        self.created: list[_FakeTexture] = []

    def texture(self, size: tuple[int, int], components: int, pixels: bytes) -> _FakeTexture:
        texture = _FakeTexture(size, components, pixels)
        self.created.append(texture)
        return texture


def _bundle_with_normal_only() -> GeneratedMaterialAtlasBundle:
    color = GeneratedAtlas(
        width=1,
        height=1,
        pixels=b"\x00\x00\x00\xff",
        uvs={"minecraft:block/stone": (0.0, 0.0, 1.0, 1.0)},
        tile_size=1,
        edge_inset_pixels=0.0,
    )
    normal = GeneratedMaterialAtlas(
        role=MaterialMapRole.NORMAL,
        width=1,
        height=1,
        pixels=b"\x80\x80\xff\xff",
        uvs=color.uvs,
        tile_size=1,
        edge_inset_pixels=0.0,
    )
    return GeneratedMaterialAtlasBundle(color=color, materials={MaterialMapRole.NORMAL: normal})


def test_material_atlas_textures_are_empty_without_bundle() -> None:
    bindings = (
        MaterialAtlasBinding(
            role=MaterialMapRole.NORMAL,
            sampler_name="u_material_normal_atlas",
            texture_unit=4,
        ),
    )

    textures = build_material_atlas_textures(_FakeContext(), None, bindings)

    assert textures == {}


def test_material_atlas_textures_create_only_present_roles() -> None:
    bindings = (
        MaterialAtlasBinding(
            role=MaterialMapRole.NORMAL,
            sampler_name="u_material_normal_atlas",
            texture_unit=4,
        ),
        MaterialAtlasBinding(
            role=MaterialMapRole.SPECULAR,
            sampler_name="u_material_specular_atlas",
            texture_unit=5,
        ),
    )
    context = _FakeContext()

    textures = build_material_atlas_textures(context, _bundle_with_normal_only(), bindings)

    assert set(textures) == {MaterialMapRole.NORMAL}
    assert textures[MaterialMapRole.NORMAL].texture_unit == 4
    assert context.created[0].size == (1, 1)
    assert context.created[0].components == 4
    assert context.created[0].pixels == b"\x80\x80\xff\xff"
    assert context.created[0].filter == (moderngl.LINEAR, moderngl.NEAREST)
    assert context.created[0].repeat_x is False
    assert context.created[0].repeat_y is False


def test_material_atlas_textures_keep_nearest_minification_for_low_end_profile() -> None:
    context = _FakeContext()

    build_material_atlas_textures(
        context,
        _bundle_with_normal_only(),
        (_normal_binding(),),
        linear_minification=False,
    )

    assert context.created[0].filter == (moderngl.NEAREST, moderngl.NEAREST)


def _normal_binding() -> MaterialAtlasBinding:
    return MaterialAtlasBinding(
        role=MaterialMapRole.NORMAL,
        sampler_name="u_material_normal_atlas",
        texture_unit=4,
    )


def _activation(
    bindings: tuple[MaterialAtlasBinding, ...],
) -> MaterialShaderActivation:
    return MaterialShaderActivation(
        shader=cast(ShaderProgram, object()),
        material_bindings=bindings,
    )


def test_activated_textures_skip_creation_without_activation() -> None:
    context = _FakeContext()

    textures = build_activated_material_atlas_textures(context, None, _bundle_with_normal_only())

    assert textures == {}
    assert context.created == []


def test_activated_textures_create_only_present_roles() -> None:
    context = _FakeContext()
    bindings = (
        _normal_binding(),
        MaterialAtlasBinding(
            role=MaterialMapRole.SPECULAR,
            sampler_name="u_material_specular_atlas",
            texture_unit=5,
        ),
    )

    textures = build_activated_material_atlas_textures(
        context, _activation(bindings), _bundle_with_normal_only()
    )

    assert set(textures) == {MaterialMapRole.NORMAL}
    assert textures[MaterialMapRole.NORMAL].texture_unit == 4
    assert len(context.created) == 1


def test_bind_material_atlas_textures_skips_empty_map() -> None:
    assert bind_material_atlas_textures({}) == ()


def test_bind_material_atlas_textures_binds_planned_units() -> None:
    context = _FakeContext()
    textures = build_activated_material_atlas_textures(
        context, _activation((_normal_binding(),)), _bundle_with_normal_only()
    )

    bound_units = bind_material_atlas_textures(textures)

    assert bound_units == (4,)
    assert context.created[0].used_units == [4]


def test_release_material_atlas_textures_releases_each_texture() -> None:
    context = _FakeContext()
    textures = build_activated_material_atlas_textures(
        context, _activation((_normal_binding(),)), _bundle_with_normal_only()
    )

    release_material_atlas_textures(textures)

    assert all(texture.released for texture in context.created)
