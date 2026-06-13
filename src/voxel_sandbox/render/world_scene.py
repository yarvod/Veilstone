# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from pathlib import Path
from typing import cast

import moderngl
import numpy as np

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import (
    CHUNK_HEIGHT,
    SECTION_SIZE,
    Chunk,
    ChunkCoord,
    ChunkSection,
    SectionCoord,
)
from voxel_sandbox.engine.generation import (
    ChunkStreamer,
    TerrainGenerator,
    WorldSeed,
    find_safe_spawn,
)
from voxel_sandbox.engine.lighting import relight_chunk
from voxel_sandbox.engine.physics import RaycastHit, voxel_raycast
from voxel_sandbox.render.atmosphere import daylight_factor, sky_color
from voxel_sandbox.render.block_highlight import BlockHighlightRenderer
from voxel_sandbox.render.camera import FirstPersonCamera
from voxel_sandbox.render.frustum import aabb_intersects_frustum
from voxel_sandbox.render.math3d import camera_matrix
from voxel_sandbox.render.meshes import (
    MeshData,
    MeshingNeighborhood,
    build_greedy_mesh,
    build_visible_face_mesh,
)
from voxel_sandbox.render.meshes.gpu_cache import SectionMeshCache
from voxel_sandbox.render.meshes.neighborhood import HALO_RADIUS, HALO_SIZE
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
        greedy_meshing: bool,
        smooth_lighting: bool,
        ambient_occlusion: bool,
        fog: bool,
        fog_start: float,
        fog_end: float,
        day_cycle_seconds: float,
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
        self.greedy_meshing = greedy_meshing
        self.smooth_lighting = smooth_lighting
        self.ambient_occlusion = ambient_occlusion
        self.fog_enabled = fog
        self.fog_start = fog_start
        self.fog_end = fog_end
        self.day_cycle_seconds = max(day_cycle_seconds, 1.0)
        self.time_of_day = 0.25
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
    def daylight(self) -> float:
        return daylight_factor(self.time_of_day)

    @property
    def clear_color(self) -> tuple[float, float, float, float]:
        return sky_color(self.daylight)

    @property
    def spawn_position(self) -> tuple[float, float, float]:
        return find_safe_spawn(
            self.get_block,
            self.generator.height_at,
            lambda block_id: self.registry.by_id(block_id).is_solid,
        )

    @property
    def loaded_chunks(self) -> int:
        return self.streamer.loaded_count

    @property
    def pending_chunks(self) -> int:
        return self.streamer.pending_count

    def get_block(self, x: int, y: int, z: int) -> int:
        return self.streamer.get_block(x, y, z)

    def is_solid_block(self, x: int, y: int, z: int) -> bool:
        return self.registry.by_id(self.get_block(x, y, z)).is_solid

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

    def update(self, delta_time: float) -> None:
        self.time_of_day = (self.time_of_day + delta_time / self.day_cycle_seconds) % 1.0

    def toggle_smooth_lighting(self) -> None:
        self.smooth_lighting = not self.smooth_lighting
        self._remesh_all()

    def toggle_ambient_occlusion(self) -> None:
        self.ambient_occlusion = not self.ambient_occlusion
        self._remesh_all()

    def toggle_fog(self) -> None:
        self.fog_enabled = not self.fog_enabled

    def toggle_mesher(self) -> None:
        self.greedy_meshing = not self.greedy_meshing
        self._remesh_all()

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
            self._remesh_horizontal_neighbors(chunk.coord)

        camera_uniform = cast("moderngl.Uniform", self.shader.program["camera_matrix"])
        texture_uniform = cast("moderngl.Uniform", self.shader.program["texture_atlas"])
        camera_position_uniform = cast("moderngl.Uniform", self.shader.program["camera_position"])
        day_tint_uniform = cast("moderngl.Uniform", self.shader.program["day_tint"])
        daylight_uniform = cast("moderngl.Uniform", self.shader.program["daylight"])
        fog_color_uniform = cast("moderngl.Uniform", self.shader.program["fog_color"])
        fog_start_uniform = cast("moderngl.Uniform", self.shader.program["fog_start"])
        fog_end_uniform = cast("moderngl.Uniform", self.shader.program["fog_end"])
        fog_enabled_uniform = cast("moderngl.Uniform", self.shader.program["fog_enabled"])
        camera_uniform.write(matrix.T.astype("f4").tobytes())
        self.texture.use(0)
        texture_uniform.value = 0
        camera_position_uniform.value = camera.position
        daylight_uniform.value = self.daylight
        day_tint_uniform.value = (
            0.55 + 0.45 * self.daylight,
            0.62 + 0.38 * self.daylight,
            0.78 + 0.22 * self.daylight,
        )
        fog_color_uniform.value = self.clear_color[:3]
        fog_start_uniform.value = self.fog_start
        fog_end_uniform.value = self.fog_end
        fog_enabled_uniform.value = int(self.fog_enabled)
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
        relight_chunk(chunk, self.registry)
        for section_y, section in enumerate(chunk.sections):
            key = SectionCoord(chunk.coord.x, section_y, chunk.coord.z)
            if not np.any(section.blocks):
                self.mesh_cache.remove(key)
                continue
            mesh = self._build_mesh(key, section)
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
        affected_chunks: set[ChunkCoord] = set()
        for world_x, world_y, world_z in coords:
            if not 0 <= world_y < CHUNK_HEIGHT:
                continue
            chunk_x = world_x // SECTION_SIZE
            chunk_z = world_z // SECTION_SIZE
            chunk = self.streamer.get_chunk(ChunkCoord(chunk_x, chunk_z))
            if chunk is not None:
                affected_chunks.add(chunk.coord)
        for chunk_coord in affected_chunks:
            chunk = self.streamer.get_chunk(chunk_coord)
            if chunk is None:
                continue
            relight_chunk(chunk, self.registry)
            self._upload_lit_chunk(chunk)

    def _upload_lit_chunk(self, chunk: Chunk) -> None:
        for section_y, section in enumerate(chunk.sections):
            key = SectionCoord(chunk.coord.x, section_y, chunk.coord.z)
            if not np.any(section.blocks):
                self.mesh_cache.remove(key)
                continue
            mesh = self._build_mesh(key, section)
            if mesh.indices.size:
                self.mesh_cache.upload(key, mesh)

    def _build_mesh(self, key: SectionCoord, section: ChunkSection) -> MeshData:
        neighborhood = self._build_neighborhood(key)
        builder = build_greedy_mesh if self.greedy_meshing else build_visible_face_mesh
        return builder(
            neighborhood,
            self.registry,
            self.atlas_uvs,
            smooth_lighting=self.smooth_lighting,
            ambient_occlusion=self.ambient_occlusion,
        )

    def _build_neighborhood(self, key: SectionCoord) -> MeshingNeighborhood:
        blocks = np.zeros((HALO_SIZE, HALO_SIZE, HALO_SIZE), dtype=np.uint16)
        sky_light = np.zeros((HALO_SIZE, HALO_SIZE, HALO_SIZE), dtype=np.uint8)
        block_light = np.zeros((HALO_SIZE, HALO_SIZE, HALO_SIZE), dtype=np.uint8)
        origin_x = key.x * SECTION_SIZE - HALO_RADIUS
        origin_y = key.y * SECTION_SIZE - HALO_RADIUS
        origin_z = key.z * SECTION_SIZE - HALO_RADIUS
        for local_x in range(HALO_SIZE):
            world_x = origin_x + local_x
            for local_y in range(HALO_SIZE):
                world_y = origin_y + local_y
                for local_z in range(HALO_SIZE):
                    world_z = origin_z + local_z
                    blocks[local_x, local_y, local_z] = self.streamer.get_block(
                        world_x, world_y, world_z
                    )
                    sky, block = self.streamer.get_light(world_x, world_y, world_z)
                    sky_light[local_x, local_y, local_z] = sky
                    block_light[local_x, local_y, local_z] = block
        return MeshingNeighborhood(blocks, sky_light, block_light)

    def _remesh_horizontal_neighbors(self, coord: ChunkCoord) -> None:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = self.streamer.get_chunk(ChunkCoord(coord.x + dx, coord.z + dz))
            if neighbor is not None:
                self._upload_lit_chunk(neighbor)

    def _remesh_all(self) -> None:
        for chunk in self.streamer.loaded_chunks():
            self._upload_lit_chunk(chunk)
