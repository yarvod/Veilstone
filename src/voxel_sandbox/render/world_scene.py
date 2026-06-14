# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

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
    split_world_axis,
)
from voxel_sandbox.engine.fluids import FLUID_MAX_LEVEL, WATER_BLOCK_ID, simulate_water_step
from voxel_sandbox.engine.generation import (
    ChunkStreamer,
    TerrainGenerator,
    WorldSeed,
    find_safe_spawn,
)
from voxel_sandbox.engine.lighting import relight_chunk
from voxel_sandbox.engine.physics import RaycastHit, voxel_raycast
from voxel_sandbox.infrastructure.storage import WorldStorage
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
    build_water_mesh,
)
from voxel_sandbox.render.meshes.gpu_cache import GpuSectionMesh, SectionMeshCache
from voxel_sandbox.render.meshes.neighborhood import HALO_RADIUS, HALO_SIZE
from voxel_sandbox.render.meshes.worker import SectionMeshWorker
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
        generation_backend: str,
        uploads_per_frame: int,
        meshing_workers: int,
        meshing_backend: str,
        mesh_uploads_per_frame: int,
        greedy_meshing: bool,
        smooth_lighting: bool,
        ambient_occlusion: bool,
        fog: bool,
        fog_start: float,
        fog_end: float,
        day_cycle_seconds: float,
        save_root: Path,
    ) -> None:
        self.context = context
        shader_root = Path(__file__).parent / "shaders" / "glsl"
        self.shader = ShaderProgram(
            context, ShaderFiles.from_directory(shader_root, "chunk_opaque")
        )
        self.water_shader = ShaderProgram(context, ShaderFiles.from_directory(shader_root, "water"))
        atlas = create_block_atlas()
        self.texture = context.texture((atlas.width, atlas.height), 4, atlas.pixels)
        self.texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.texture.build_mipmaps()
        self.registry = create_core_block_registry()
        self.atlas_uvs = atlas.uvs
        self.uploads_per_frame = uploads_per_frame
        self.mesh_uploads_per_frame = mesh_uploads_per_frame
        self.greedy_meshing = greedy_meshing
        self.smooth_lighting = smooth_lighting
        self.ambient_occlusion = ambient_occlusion
        self.fog_enabled = fog
        self.fog_start = fog_start
        self.fog_end = fog_end
        self.day_cycle_seconds = max(day_cycle_seconds, 1.0)
        self.time_of_day = 0.25
        self.animation_time = 0.0
        self._fluid_accumulator = 0.0
        self._fluid_chunk_cursor = 0
        self.remote_mode = False
        self.storage = WorldStorage(save_root)
        metadata = self.storage.load_metadata()
        active_seed = metadata.seed if metadata is not None else seed
        self.seed_text = active_seed
        self.storage.ensure_world(name="Development World", seed=active_seed)
        self.generator = TerrainGenerator(WorldSeed.parse(active_seed))
        self.streamer = ChunkStreamer(
            self.generator,
            render_distance=render_distance,
            workers=generation_workers,
            backend=cast(Literal["thread", "process"], generation_backend),
            prepare_lighting=True,
            storage=self.storage,
        )
        if self.shader.program is None or self.water_shader.program is None:
            raise RuntimeError("World shaders failed to compile")
        self.mesh_cache = SectionMeshCache(context, self.shader.program)
        self.water_mesh_cache = SectionMeshCache(context, self.water_shader.program)
        self.mesh_worker = SectionMeshWorker(
            self.registry,
            self.atlas_uvs,
            workers=meshing_workers,
            backend=cast(Literal["thread", "process"], meshing_backend),
        )
        self.highlight = BlockHighlightRenderer(context)
        self.visible_sections = 0
        self.draw_calls = 0
        self.face_count = 0
        self.triangle_count = 0
        self.selection: RaycastHit | None = None
        self._upload_chunk_sync(self.streamer.prime(ChunkCoord(0, 0)))

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
            lambda block_id: (
                self.registry.by_id(block_id).is_solid or self.registry.by_id(block_id).is_fluid
            ),
        )

    @property
    def loaded_chunks(self) -> int:
        return self.streamer.loaded_count

    @property
    def pending_chunks(self) -> int:
        return self.streamer.pending_count

    @property
    def pending_meshes(self) -> int:
        return self.mesh_worker.pending_count

    def get_block(self, x: int, y: int, z: int) -> int:
        return self.streamer.get_block(x, y, z)

    def is_solid_block(self, x: int, y: int, z: int) -> bool:
        if y < 0:
            return True
        if y >= CHUNK_HEIGHT:
            return False
        chunk_x, _ = split_world_axis(x)
        chunk_z, _ = split_world_axis(z)
        if self.streamer.get_chunk(ChunkCoord(chunk_x, chunk_z)) is None:
            return True
        return self.registry.by_id(self.get_block(x, y, z)).is_solid

    def ensure_collision_area_loaded(self, x: float, z: float, radius: float) -> None:
        min_chunk_x, _ = split_world_axis(int(np.floor(x - radius)))
        max_chunk_x, _ = split_world_axis(int(np.floor(x + radius)))
        min_chunk_z, _ = split_world_axis(int(np.floor(z - radius)))
        max_chunk_z, _ = split_world_axis(int(np.floor(z + radius)))
        for chunk_x in range(min_chunk_x, max_chunk_x + 1):
            for chunk_z in range(min_chunk_z, max_chunk_z + 1):
                coord = ChunkCoord(chunk_x, chunk_z)
                if self.streamer.get_chunk(coord) is not None:
                    continue
                self._upload_chunk_sync(self.streamer.prime(coord))

    def raycast(
        self,
        origin: tuple[float, float, float],
        direction: tuple[float, float, float],
        max_distance: float = 6.0,
    ) -> RaycastHit | None:
        return voxel_raycast(self.get_block, origin, direction, max_distance)

    def set_block(self, block: tuple[int, int, int], block_id: int) -> bool:
        if block_id == WATER_BLOCK_ID:
            changed = self.streamer.set_fluid(*block, block_id, FLUID_MAX_LEVEL)
        else:
            changed = self.streamer.set_block(*block, block_id)
        if not changed:
            return False
        self._remesh_around(block)
        return True

    def update(self, delta_time: float) -> None:
        self.time_of_day = (self.time_of_day + delta_time / self.day_cycle_seconds) % 1.0
        self.animation_time += delta_time
        self._fluid_accumulator += delta_time
        if self._fluid_accumulator < 0.2:
            return
        self._fluid_accumulator %= 0.2
        chunks = self.streamer.loaded_chunks()
        if not chunks:
            return
        chunk = chunks[self._fluid_chunk_cursor % len(chunks)]
        self._fluid_chunk_cursor += 1
        if simulate_water_step(chunk).changed:
            relight_chunk(chunk, self.registry)
            self._schedule_chunk(chunk)

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
        if not self.remote_mode:
            batch = self.streamer.update(center, max_completed=self.uploads_per_frame)
            for coord in batch.unloaded:
                self._remove_chunk(coord)
            for chunk in batch.loaded:
                self._schedule_chunk(chunk)
                self._schedule_horizontal_neighbors(chunk.coord)
        for completed in self.mesh_worker.poll(self.mesh_uploads_per_frame):
            if self.streamer.get_chunk(completed.key.chunk) is None:
                continue
            if completed.mesh.indices.size:
                self.mesh_cache.upload(completed.key, completed.mesh)
            else:
                self.mesh_cache.remove(completed.key)
            if completed.transparent_mesh.indices.size:
                self.water_mesh_cache.upload(completed.key, completed.transparent_mesh)
            else:
                self.water_mesh_cache.remove(completed.key)

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
        underwater = self.registry.by_id(
            self.get_block(
                int(np.floor(camera.x)),
                int(np.floor(camera.y)),
                int(np.floor(camera.z)),
            )
        ).is_fluid
        active_fog_color = (0.035, 0.16, 0.24) if underwater else self.clear_color[:3]
        active_fog_start = 0.0 if underwater else self.fog_start
        active_fog_end = 12.0 if underwater else self.fog_end
        fog_color_uniform.value = active_fog_color
        fog_start_uniform.value = active_fog_start
        fog_end_uniform.value = active_fog_end
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
        self._render_water(
            matrix,
            camera,
            active_fog_color,
            active_fog_start,
            active_fog_end,
        )
        self.selection = self.raycast(camera.position, camera.direction)
        if self.selection is not None:
            self.highlight.render(matrix, self.selection.block)

    def release(self) -> None:
        self.mesh_worker.close()
        self.streamer.close()
        self.highlight.release()
        self.water_mesh_cache.release()
        self.mesh_cache.release()
        self.texture.release()
        self.shader.release()
        self.water_shader.release()

    def autosave(self) -> int:
        self.storage.ensure_world(name="Development World", seed=self.seed_text)
        return self.streamer.save_dirty()

    def install_remote_chunk(self, chunk: Chunk) -> None:
        relight_chunk(chunk, self.registry)
        self.streamer.install_chunk(chunk)
        self._schedule_chunk(chunk)

    def enable_remote_mode(self) -> None:
        self.remote_mode = True

    def _upload_chunk_sync(self, chunk: Chunk) -> None:
        for section_y, section in enumerate(chunk.sections):
            key = SectionCoord(chunk.coord.x, section_y, chunk.coord.z)
            if not np.any(section.blocks):
                self.mesh_cache.remove(key)
                self.water_mesh_cache.remove(key)
                continue
            mesh, water_mesh = self._build_mesh(key, section)
            if mesh.indices.size:
                self.mesh_cache.upload(key, mesh)
            if water_mesh.indices.size:
                self.water_mesh_cache.upload(key, water_mesh)

    def _remove_chunk(self, coord: ChunkCoord) -> None:
        self.mesh_worker.invalidate_chunk(coord.x, coord.z)
        for section_y in range(CHUNK_HEIGHT // SECTION_SIZE):
            key = SectionCoord(coord.x, section_y, coord.z)
            self.mesh_cache.remove(key)
            self.water_mesh_cache.remove(key)

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
            self._schedule_chunk(chunk)

    def _schedule_chunk(self, chunk: Chunk) -> None:
        for section_y, section in enumerate(chunk.sections):
            key = SectionCoord(chunk.coord.x, section_y, chunk.coord.z)
            if not np.any(section.blocks):
                self.mesh_cache.remove(key)
                self.water_mesh_cache.remove(key)
                continue
            self.mesh_worker.submit(
                key,
                self._build_neighborhood(key),
                greedy=self.greedy_meshing,
                smooth_lighting=self.smooth_lighting,
                ambient_occlusion=self.ambient_occlusion,
            )

    def _build_mesh(self, key: SectionCoord, section: ChunkSection) -> tuple[MeshData, MeshData]:
        neighborhood = self._build_neighborhood(key)
        builder = build_greedy_mesh if self.greedy_meshing else build_visible_face_mesh
        return (
            builder(
                neighborhood,
                self.registry,
                self.atlas_uvs,
                smooth_lighting=self.smooth_lighting,
                ambient_occlusion=self.ambient_occlusion,
            ),
            build_water_mesh(neighborhood, self.registry, self.atlas_uvs),
        )

    def _build_neighborhood(self, key: SectionCoord) -> MeshingNeighborhood:
        origin = (
            key.x * SECTION_SIZE - HALO_RADIUS,
            key.y * SECTION_SIZE - HALO_RADIUS,
            key.z * SECTION_SIZE - HALO_RADIUS,
        )
        blocks, sky_light, block_light, metadata = self.streamer.snapshot_region(
            origin,
            (HALO_SIZE, HALO_SIZE, HALO_SIZE),
        )
        return MeshingNeighborhood(blocks, sky_light, block_light, metadata)

    def _render_water(
        self,
        matrix: np.ndarray,
        camera: FirstPersonCamera,
        fog_color: tuple[float, float, float],
        fog_start: float,
        fog_end: float,
    ) -> None:
        program = self.water_shader.program
        if program is None:
            return
        cast("moderngl.Uniform", program["camera_matrix"]).write(matrix.T.astype("f4").tobytes())
        cast("moderngl.Uniform", program["texture_atlas"]).value = 0
        cast("moderngl.Uniform", program["camera_position"]).value = camera.position
        cast("moderngl.Uniform", program["animation_time"]).value = self.animation_time
        cast("moderngl.Uniform", program["fog_color"]).value = fog_color
        cast("moderngl.Uniform", program["fog_start"]).value = fog_start
        cast("moderngl.Uniform", program["fog_end"]).value = fog_end
        cast("moderngl.Uniform", program["fog_enabled"]).value = int(self.fog_enabled)
        origin_uniform = cast("moderngl.Uniform", program["section_origin"])
        visible: list[tuple[float, SectionCoord, GpuSectionMesh]] = []
        for key, gpu_mesh in self.water_mesh_cache.items():
            origin = (key.x * SECTION_SIZE, key.y * SECTION_SIZE, key.z * SECTION_SIZE)
            minimum = (float(origin[0]), float(origin[1]), float(origin[2]))
            maximum = (
                float(origin[0] + SECTION_SIZE),
                float(origin[1] + SECTION_SIZE),
                float(origin[2] + SECTION_SIZE),
            )
            if not aabb_intersects_frustum(matrix, minimum, maximum):
                continue
            center = tuple(value + SECTION_SIZE * 0.5 for value in origin)
            distance = sum((center[i] - camera.position[i]) ** 2 for i in range(3))
            visible.append((distance, key, gpu_mesh))

        self.context.enable(moderngl.BLEND)
        self.context.disable(moderngl.CULL_FACE)
        self.context.depth_mask = False  # pyright: ignore[reportAttributeAccessIssue]
        self.context.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        for _distance, key, gpu_mesh in sorted(visible, reverse=True, key=lambda item: item[0]):
            origin_uniform.value = (
                key.x * SECTION_SIZE,
                key.y * SECTION_SIZE,
                key.z * SECTION_SIZE,
            )
            gpu_mesh.vertex_array.render(moderngl.TRIANGLES)
            self.draw_calls += 1
            self.face_count += gpu_mesh.data.face_count
            self.triangle_count += gpu_mesh.data.triangle_count
        self.context.depth_mask = True  # pyright: ignore[reportAttributeAccessIssue]
        self.context.disable(moderngl.BLEND)
        self.context.enable(moderngl.CULL_FACE)

    def _schedule_horizontal_neighbors(self, coord: ChunkCoord) -> None:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = self.streamer.get_chunk(ChunkCoord(coord.x + dx, coord.z + dz))
            if neighbor is not None:
                self._schedule_chunk(neighbor)

    def _remesh_all(self) -> None:
        for chunk in self.streamer.loaded_chunks():
            self._schedule_chunk(chunk)
