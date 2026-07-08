from __future__ import annotations

from voxel_sandbox.render.material_binding import MaterialAtlasBinding
from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.material_textures import build_material_atlas_textures
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
    assert context.created[0].repeat_x is False
    assert context.created[0].repeat_y is False
