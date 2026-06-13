# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from pathlib import Path
from typing import cast

import moderngl
import numpy as np

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import CHUNK_HEIGHT, SECTION_SIZE, Chunk, ChunkCoord, SectionCoord
from voxel_sandbox.engine.generation import ChunkStreamer, TerrainGenerator, WorldSeed
from voxel_sandbox.engine.physics import RaycastHit, voxel_raycast
from voxel_sandbox.render.block_highlight import BlockHighlightRenderer
from voxel_sandbox.render.camera import FirstPersonCamera
from voxel_sandbox.render.frustum import aabb_intersects_frustum
from voxel_sandbox.render.math3d import camera_matrix
from voxel_sandbox.render.meshes import build_visible_face_mesh
from voxel_sandbox.render.meshes.gpu_cache import SectionMeshCache
from voxel_sandbox.render.shaders.loader import ShaderFiles, ShaderProgram
from voxel_sandbox.render.texture_atlas import create_block_atlas


class DemoWorldRenderer:
    def __init__(
        self,
        context: moderngl.Context,
        *,
        seed: str,
        render_distance: int,
        generation_workers: int,
        uploads_per_frame: int,
    ) -> None:
        self.context = context
        shader_root = Path(__file__).parent / "shaders" / "glsl"
        self.shader = ShaderProgram(
            context, ShaderFiles.from_directory(shader_root, "chunk_opaque")
        )
        atlas = create_block_atlas()
        self.texture = context.texture((atlas.width, atlas.height), 4, atlas.pixels)
        self.texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.texture.build_mipmaps()
        self.registry = create_core_block_registry()
        self.atlas_uvs = atlas.uvs
        self.uploads_per_frame = uploads_per_frame
        self.generator = TerrainGenerator(WorldSeed.parse(seed))
        self.streamer = ChunkStreamer(
            self.generator,
            render_distance=render_distance,
            workers=generation_workers,
        )
        if self.shader.program is None:
            raise RuntimeError("Chunk shader failed to compile")
        self.mesh_cache = SectionMeshCache(context, self.shader.program)
        self.highlight = BlockHighlightRenderer(context)
        self.visible_sections = 0
        self.draw_calls = 0
        self.face_count = 0
        self.triangle_count = 0
        self.selection: RaycastHit | None = None
        self._upload_chunk(self.streamer.prime(ChunkCoord(0, 0)))

    @property
    def spawn_position(self) -> tuple[float, float, float]:
        x, z = 8.5, 8.5
        return x, float(self.generator.height_at(8, 8) + 2), z

    @property
    def loaded_chunks(self) -> int:
        return self.streamer.loaded_count

    @property
    def pending_chunks(self) -> int:
        return self.streamer.pending_count

    def get_block(self, x: int, y: int, z: int) -> int:
        return self.streamer.get_block(x, y, z)

    def raycast(
        self,
        origin: tuple[float, float, float],
        direction: tuple[float, float, float],
        max_distance: float = 6.0,
    ) -> RaycastHit | None:
        return voxel_raycast(self.get_block, origin, direction, max_distance)

    def set_block(self, block: tuple[int, int, int], block_id: int) -> bool:
        if not self.streamer.set_block(*block, block_id):
            return False
        self._remesh_around(block)
        return True

    def render(self, camera: FirstPersonCamera, width: int, height: int, fov: float) -> None:
        if self.shader.program is None:
            return
        matrix = camera_matrix(camera, max(width, 1) / max(height, 1), fov)
        center = ChunkCoord(
            int(np.floor(camera.x / SECTION_SIZE)),
            int(np.floor(camera.z / SECTION_SIZE)),
        )
        batch = self.streamer.update(center, max_completed=self.uploads_per_frame)
        for coord in batch.unloaded:
            self._remove_chunk(coord)
        for chunk in batch.loaded:
            self._upload_chunk(chunk)

        camera_uniform = cast("moderngl.Uniform", self.shader.program["camera_matrix"])
        texture_uniform = cast("moderngl.Uniform", self.shader.program["texture_atlas"])
        camera_uniform.write(matrix.T.astype("f4").tobytes())
        self.texture.use(0)
        texture_uniform.value = 0
        origin_uniform = cast("moderngl.Uniform", self.shader.program["section_origin"])
        self.visible_sections = 0
        self.draw_calls = 0
        self.face_count = 0
        self.triangle_count = 0
        for key, gpu_mesh in self.mesh_cache.items():
            origin = (key.x * SECTION_SIZE, key.y * SECTION_SIZE, key.z * SECTION_SIZE)
            minimum = (float(origin[0]), float(origin[1]), float(origin[2]))
            maximum = (
                float(origin[0] + SECTION_SIZE),
                float(origin[1] + SECTION_SIZE),
                float(origin[2] + SECTION_SIZE),
            )
            if not aabb_intersects_frustum(matrix, minimum, maximum):
                continue
            origin_uniform.value = origin
            gpu_mesh.vertex_array.render(moderngl.TRIANGLES)
            self.visible_sections += 1
            self.draw_calls += 1
            self.face_count += gpu_mesh.data.face_count
            self.triangle_count += gpu_mesh.data.triangle_count
        self.selection = self.raycast(camera.position, camera.direction)
        if self.selection is not None:
            self.highlight.render(matrix, self.selection.block)

    def release(self) -> None:
        self.streamer.close()
        self.highlight.release()
        self.mesh_cache.release()
        self.texture.release()
        self.shader.release()

    def _upload_chunk(self, chunk: Chunk) -> None:
        for section_y, section in enumerate(chunk.sections):
            key = SectionCoord(chunk.coord.x, section_y, chunk.coord.z)
            if not np.any(section.blocks):
                self.mesh_cache.remove(key)
                continue
            mesh = build_visible_face_mesh(section, self.registry, self.atlas_uvs)
            if mesh.indices.size:
                self.mesh_cache.upload(key, mesh)

    def _remove_chunk(self, coord: ChunkCoord) -> None:
        for section_y in range(CHUNK_HEIGHT // SECTION_SIZE):
            self.mesh_cache.remove(SectionCoord(coord.x, section_y, coord.z))

    def _remesh_around(self, block: tuple[int, int, int]) -> None:
        x, y, z = block
        coords = {(x, y, z)}
        if x % SECTION_SIZE in {0, SECTION_SIZE - 1}:
            coords.add((x - 1 if x % SECTION_SIZE == 0 else x + 1, y, z))
        if y % SECTION_SIZE in {0, SECTION_SIZE - 1}:
            coords.add((x, y - 1 if y % SECTION_SIZE == 0 else y + 1, z))
        if z % SECTION_SIZE in {0, SECTION_SIZE - 1}:
            coords.add((x, y, z - 1 if z % SECTION_SIZE == 0 else z + 1))
        for world_x, world_y, world_z in coords:
            if not 0 <= world_y < CHUNK_HEIGHT:
                continue
            chunk_x, local_x = divmod(world_x, SECTION_SIZE)
            chunk_z, local_z = divmod(world_z, SECTION_SIZE)
            del local_x, local_z
            section_y = world_y // SECTION_SIZE
            chunk = self.streamer.get_chunk(ChunkCoord(chunk_x, chunk_z))
            key = SectionCoord(chunk_x, section_y, chunk_z)
            if chunk is None:
                self.mesh_cache.remove(key)
                continue
            section = chunk.sections[section_y]
            if not np.any(section.blocks):
                self.mesh_cache.remove(key)
                continue
            mesh = build_visible_face_mesh(section, self.registry, self.atlas_uvs)
            self.mesh_cache.upload(key, mesh)
