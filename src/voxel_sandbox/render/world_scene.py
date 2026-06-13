# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from pathlib import Path
from typing import cast

import moderngl

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import SECTION_SIZE, ChunkSection, SectionCoord
from voxel_sandbox.render.camera import FirstPersonCamera
from voxel_sandbox.render.frustum import aabb_intersects_frustum
from voxel_sandbox.render.math3d import camera_matrix
from voxel_sandbox.render.meshes import MeshData, build_visible_face_mesh
from voxel_sandbox.render.meshes.gpu_cache import SectionMeshCache
from voxel_sandbox.render.shaders.loader import ShaderFiles, ShaderProgram
from voxel_sandbox.render.texture_atlas import create_block_atlas


class DemoWorldRenderer:
    SECTION_KEY = SectionCoord(0, 0, 0)

    def __init__(self, context: moderngl.Context) -> None:
        self.context = context
        shader_root = Path(__file__).parent / "shaders" / "glsl"
        self.shader = ShaderProgram(
            context, ShaderFiles.from_directory(shader_root, "chunk_opaque")
        )
        atlas = create_block_atlas()
        self.texture = context.texture((atlas.width, atlas.height), 4, atlas.pixels)
        self.texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.texture.build_mipmaps()
        section = _create_demo_section()
        mesh = build_visible_face_mesh(
            section,
            create_core_block_registry(),
            atlas.uvs,
        )
        if self.shader.program is None:
            raise RuntimeError("Chunk shader failed to compile")
        self.mesh_cache = SectionMeshCache(context, self.shader.program)
        self.mesh_cache.upload(self.SECTION_KEY, mesh)

    @property
    def mesh(self) -> MeshData:
        gpu_mesh = self.mesh_cache.get(self.SECTION_KEY)
        if gpu_mesh is None:
            raise RuntimeError("Demo section mesh is not uploaded")
        return gpu_mesh.data

    def render(self, camera: FirstPersonCamera, width: int, height: int, fov: float) -> None:
        if self.shader.program is None:
            return
        matrix = camera_matrix(camera, max(width, 1) / max(height, 1), fov)
        camera_uniform = cast("moderngl.Uniform", self.shader.program["camera_matrix"])
        texture_uniform = cast("moderngl.Uniform", self.shader.program["texture_atlas"])
        camera_uniform.write(matrix.T.astype("f4").tobytes())
        self.texture.use(0)
        texture_uniform.value = 0
        gpu_mesh = self.mesh_cache.get(self.SECTION_KEY)
        if gpu_mesh is None:
            return
        origin = (
            self.SECTION_KEY.x * SECTION_SIZE,
            self.SECTION_KEY.y * SECTION_SIZE,
            self.SECTION_KEY.z * SECTION_SIZE,
        )
        minimum = (float(origin[0]), float(origin[1]), float(origin[2]))
        maximum = (
            float(origin[0] + SECTION_SIZE),
            float(origin[1] + SECTION_SIZE),
            float(origin[2] + SECTION_SIZE),
        )
        if not aabb_intersects_frustum(matrix, minimum, maximum):
            return
        origin_uniform = cast("moderngl.Uniform", self.shader.program["section_origin"])
        origin_uniform.value = origin
        gpu_mesh.vertex_array.render(moderngl.TRIANGLES)

    def release(self) -> None:
        self.mesh_cache.release()
        self.texture.release()
        self.shader.release()


def _create_demo_section() -> ChunkSection:
    section = ChunkSection()
    for x in range(16):
        for z in range(16):
            height = 4 + ((x // 4 + z // 5) % 3)
            section.blocks[x, : height - 2, z] = 1
            section.blocks[x, height - 2 : height - 1, z] = 2
            section.blocks[x, height - 1 : height, z] = 3
    return section
