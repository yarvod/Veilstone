# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from pathlib import Path
from time import perf_counter
from typing import Literal, cast

import moderngl
import numpy as np

from voxel_sandbox.app.composition import (
    WorldSceneDependencies,
    build_world_scene_dependencies,
)
from voxel_sandbox.app.paths import resource_path
from voxel_sandbox.engine.chunks import (
    CHUNK_HEIGHT,
    SECTION_SIZE,
    Chunk,
    ChunkCoord,
    ChunkSection,
    SectionCoord,
    split_world_axis,
)
from voxel_sandbox.engine.fluids import (
    FLUID_MAX_LEVEL,
    WATER_BLOCK_ID,
    chunk_contains_water,
    simulate_water_step,
)
from voxel_sandbox.engine.generation import find_safe_spawn
from voxel_sandbox.engine.lighting import effective_light_level, relight_chunks
from voxel_sandbox.engine.physics import RaycastHit, collision_chunk_footprint, voxel_raycast
from voxel_sandbox.render.atmosphere import (
    celestial_light_direction,
    daylight_factor,
    sky_color,
)
from voxel_sandbox.render.block_highlight import BlockHighlightRenderer
from voxel_sandbox.render.camera import FirstPersonCamera
from voxel_sandbox.render.frustum import Frustum
from voxel_sandbox.render.material_metadata import MaterialMapRole
from voxel_sandbox.render.material_quality import (
    MaterialPipelineDecision,
    resolve_material_pipeline_from_graphics,
)
from voxel_sandbox.render.material_shader_runtime import (
    MaterialShaderActivation,
    MaterialShaderRuntimeWiring,
    activate_material_shader,
    apply_material_sampler_bindings,
    build_material_shader_runtime_wiring,
    resolve_chunk_draw_shader,
)
from voxel_sandbox.render.material_shader_setup import (
    MaterialShaderSetup,
    build_material_shader_setup,
)
from voxel_sandbox.render.material_textures import (
    MaterialAtlasTexture,
    bind_material_atlas_textures,
    build_activated_material_atlas_textures,
    release_material_atlas_textures,
)
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
from voxel_sandbox.render.perf import RenderQueueSnapshot, StreamingStageSample
from voxel_sandbox.render.shaders.loader import ShaderFiles, ShaderProgram
from voxel_sandbox.render.shadows import ShadowMap, shadow_map_size, sun_light_matrix
from voxel_sandbox.render.streaming_schedule import (
    chunk_distance,
    chunk_visible,
    drain_grouped_priority_keys,
    frame_budget,
    streaming_priority,
)
from voxel_sandbox.render.texture_atlas import GeneratedAtlas, GeneratedMaterialAtlasBundle
from voxel_sandbox.render.texture_packs.importer import (
    load_active_block_atlas,
    load_material_atlas_bundle,
)

_PIPELINE_DIAGNOSTIC_INTERVAL_SECONDS = 0.5


def _configure_block_texture(
    texture: moderngl.Texture,
    *,
    linear_minification: bool = True,
) -> None:
    if linear_minification:
        texture.build_mipmaps(max_level=1)
        minification_filter = moderngl.LINEAR_MIPMAP_LINEAR
    else:
        minification_filter = moderngl.NEAREST
    texture.filter = (minification_filter, moderngl.NEAREST)
    texture.repeat_x = False
    texture.repeat_y = False


def _atlas_tile_margin(atlas: GeneratedAtlas) -> float:
    if atlas.gutter_pixels > 0:
        return 0.0
    if atlas.tile_size <= 0 or atlas.edge_inset_pixels <= 0.0:
        return 0.0
    return min(0.25, atlas.edge_inset_pixels / atlas.tile_size)


def _outside_fog_range(
    position: tuple[float, float, float],
    minimum: tuple[float, float, float],
    maximum: tuple[float, float, float],
    fog_end: float,
) -> bool:
    distance_squared = 0.0
    for coordinate, lower, upper in zip(position, minimum, maximum, strict=True):
        if coordinate < lower:
            distance_squared += (lower - coordinate) ** 2
        elif coordinate > upper:
            distance_squared += (coordinate - upper) ** 2
    return distance_squared > fog_end * fog_end


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
        shadow_quality: str,
        shadow_bias: float,
        save_root: Path,
        resource_pack_path: str = "",
        material_quality: str = "color-only",
        water_detail: bool = True,
        linear_texture_minification: bool = True,
        opaque_batch_chunks: int = 1,
        world_dependencies: WorldSceneDependencies | None = None,
    ) -> None:
        self.context = context
        shader_root = Path(__file__).parent / "shaders" / "glsl"
        self.shader = ShaderProgram(
            context, ShaderFiles.from_directory(shader_root, "chunk_opaque")
        )
        self.water_shader = ShaderProgram(context, ShaderFiles.from_directory(shader_root, "water"))
        self.shadow_shader = ShaderProgram(
            context, ShaderFiles.from_directory(shader_root, "shadow_depth")
        )
        if world_dependencies is None:
            world_dependencies = build_world_scene_dependencies(
                seed=seed,
                save_root=save_root,
                render_distance=render_distance,
                generation_workers=generation_workers,
                generation_backend=generation_backend,
            )
        self._storage = world_dependencies.storage
        self._registry = world_dependencies.block_registry
        self._generator = world_dependencies.generation
        self._streamer = world_dependencies.streaming
        self.world_name = world_dependencies.world_name
        self.seed_text = world_dependencies.seed_text

        pack_path = Path(resource_pack_path) if resource_pack_path else None
        atlas = load_active_block_atlas(
            pack_path,
            registry=self._registry,
            cache_root=save_root.parent / "texture_cache",
        )
        self.linear_texture_minification = linear_texture_minification
        self.opaque_batch_chunks = opaque_batch_chunks
        self.texture = context.texture((atlas.width, atlas.height), 4, atlas.pixels)
        _configure_block_texture(
            self.texture,
            linear_minification=self.linear_texture_minification,
        )
        self._atlas = atlas
        self._shader_root = shader_root
        self.atlas_uvs = atlas.uvs
        self.atlas_tile_margin = _atlas_tile_margin(atlas)
        self.uploads_per_frame = uploads_per_frame
        self.mesh_uploads_per_frame = mesh_uploads_per_frame
        self.greedy_meshing = greedy_meshing
        self.smooth_lighting = smooth_lighting
        self.ambient_occlusion = ambient_occlusion
        self.fog_enabled = fog
        self.fog_start = fog_start
        self.fog_end = fog_end
        self.day_cycle_seconds = day_cycle_seconds
        self.shadow_quality = shadow_quality
        self.shadow_bias = shadow_bias
        self.water_detail_enabled = water_detail
        self.material_pipeline: MaterialPipelineDecision = resolve_material_pipeline_from_graphics(
            material_quality
        )
        self.material_bundle: GeneratedMaterialAtlasBundle | None = None
        material_roles = ()
        if self.material_pipeline.build_material_bundle:
            material_pack_path = pack_path or resource_path("resource_packs/default")
            self.material_bundle = load_material_atlas_bundle(material_pack_path, atlas)
            material_roles = self.material_bundle.materials.keys()
        self.material_shader_setup: MaterialShaderSetup = build_material_shader_setup(
            self.material_pipeline,
            material_roles,
        )

        self.material_shader_wiring: MaterialShaderRuntimeWiring = (
            build_material_shader_runtime_wiring(
                self.material_shader_setup,
                shader_root,
            )
        )
        self.material_shader_activation: MaterialShaderActivation | None = activate_material_shader(
            context, self.material_shader_wiring
        )
        self.material_atlas_textures: dict[MaterialMapRole, MaterialAtlasTexture] = (
            build_activated_material_atlas_textures(
                context,
                self.material_shader_activation,
                self.material_bundle,
                linear_minification=self.linear_texture_minification,
            )
        )
        apply_material_sampler_bindings(self.material_shader_activation)
        if self.material_shader_activation is not None:
            # Material-preview draws chunks with the activated shader; the
            # default chunk shader is released since nothing references it.
            self.shader.release()
        self.shader = resolve_chunk_draw_shader(self.shader, self.material_shader_activation)
        shadow_size = shadow_map_size(shadow_quality)
        self.shadow_map = ShadowMap.create(context, shadow_size) if shadow_size else None
        self._neutral_shadow_texture = context.depth_texture((1, 1))
        self._neutral_shadow_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self._neutral_shadow_texture.compare_func = "<="
        neutral_shadow_framebuffer = context.framebuffer(
            depth_attachment=self._neutral_shadow_texture
        )
        neutral_shadow_framebuffer.clear(depth=1.0)
        neutral_shadow_framebuffer.release()
        self.time_of_day = 0.18
        self.animation_time = 0.0
        self.vegetation_wind_enabled = True
        self._fluid_accumulator = 0.0
        self._fluid_active_chunks: set[ChunkCoord] = set()
        self.remote_mode = False
        self._stream_relight_queue: dict[ChunkCoord, None] = {}
        self._stream_remesh_queue: dict[ChunkCoord, None] = {}
        self._stream_mesh_active: set[ChunkCoord] = set()
        self._stream_relight_active: set[ChunkCoord] = set()
        self._streaming_frustum: Frustum | None = None
        if (
            self.shader.program is None
            or self.water_shader.program is None
            or self.shadow_shader.program is None
        ):
            raise RuntimeError("World shaders failed to compile")
        self.mesh_cache = SectionMeshCache(
            context,
            self.shader.program,
            self.shadow_shader.program if self.shadow_map is not None else None,
            batch_chunks=self.opaque_batch_chunks,
            batch_vertical_sections=True,
        )
        self.water_mesh_cache = SectionMeshCache(
            context,
            self.water_shader.program,
            wind_motion=False,
            shoreline_factor=True,
        )
        self._meshing_workers = meshing_workers
        self._meshing_backend = cast(Literal["thread", "process"], meshing_backend)
        self.mesh_worker = SectionMeshWorker(
            self._registry,
            self.atlas_uvs,
            workers=self._meshing_workers,
            backend=self._meshing_backend,
        )
        self.highlight = BlockHighlightRenderer(context)
        self.visible_sections = 0
        self.draw_calls = 0
        self._completed_gpu_uploads = 0
        self._dirty_chunk_sample = self._streamer.dirty_chunk_count
        self._next_pipeline_diagnostic_sample = (
            perf_counter() + _PIPELINE_DIAGNOSTIC_INTERVAL_SECONDS
        )
        self._streaming_stage_profiling = False
        self.last_streaming_stage_sample = StreamingStageSample()
        self.face_count = 0
        self.triangle_count = 0
        self.selection: RaycastHit | None = None
        initial_chunk = self._streamer.prime(ChunkCoord(0, 0))
        if chunk_contains_water(initial_chunk):
            self._fluid_active_chunks.add(initial_chunk.coord)
        self._upload_chunk_sync(initial_chunk)

    @property
    def daylight(self) -> float:
        return daylight_factor(self.time_of_day)

    @property
    def light_direction(self) -> tuple[float, float, float]:
        return celestial_light_direction(self.time_of_day)

    @property
    def clear_color(self) -> tuple[float, float, float, float]:
        return sky_color(self.daylight)

    def spawn_light_level(self, x: int, y: int, z: int) -> int | None:
        chunk_x, _local_x = split_world_axis(x)
        chunk_z, _local_z = split_world_axis(z)
        if self._streamer.get_chunk(ChunkCoord(chunk_x, chunk_z)) is None:
            return None
        samples = (self._streamer.get_light(x, y, z), self._streamer.get_light(x, y + 1, z))
        return max(
            effective_light_level(sky_light, block_light, self.daylight)
            for sky_light, block_light in samples
        )

    def entity_light(
        self,
        position: tuple[float, float, float],
        height: float,
    ) -> tuple[float, float]:
        x = int(np.floor(position[0]))
        z = int(np.floor(position[2]))
        sample_heights = {
            max(0, min(CHUNK_HEIGHT - 1, int(np.floor(position[1] + height * amount))))
            for amount in (0.15, 0.55, 0.9)
        }
        samples = [self._streamer.get_light(x, y, z) for y in sample_heights]
        return (
            max((sky for sky, _block in samples), default=0) / 15.0,
            max((block for _sky, block in samples), default=0) / 15.0,
        )

    @property
    def spawn_position(self) -> tuple[float, float, float]:
        try:
            return find_safe_spawn(
                self.get_block,
                self._generator.height_at,
                lambda block_id: (
                    self._registry.by_id(block_id).is_solid
                    or self._registry.by_id(block_id).is_fluid
                ),
                prepare_column=lambda x, z: self.ensure_collision_area_loaded(
                    float(x) + 0.5,
                    float(z) + 0.5,
                    0.0,
                ),
            )
        except RuntimeError:
            return self._create_emergency_spawn(8, 8)

    @property
    def loaded_chunks(self) -> int:
        return self._streamer.loaded_count

    @property
    def pending_chunks(self) -> int:
        return self._streamer.pending_count

    @property
    def pending_meshes(self) -> int:
        return self.mesh_worker.pending_count

    @property
    def water_mesh_sections(self) -> int:
        return sum(1 for _key, _mesh in self.water_mesh_cache.items())

    @property
    def water_mesh_triangles(self) -> int:
        return sum(
            gpu_mesh.data.indices.size // 3 for _key, gpu_mesh in self.water_mesh_cache.items()
        )

    @property
    def water_shore_vertices(self) -> int:
        return sum(
            int(np.count_nonzero(gpu_mesh.data.vertices[:, 10] > 0.0))
            for _key, gpu_mesh in self.water_mesh_cache.items()
        )

    def perf_queues(self) -> RenderQueueSnapshot:
        now = perf_counter()
        if now >= self._next_pipeline_diagnostic_sample:
            self._dirty_chunk_sample = self._streamer.dirty_chunk_count
            self._next_pipeline_diagnostic_sample = now + _PIPELINE_DIAGNOSTIC_INTERVAL_SECONDS
        return RenderQueueSnapshot(
            loaded_chunks=self.loaded_chunks,
            pending_chunks=self.pending_chunks,
            pending_meshes=self.pending_meshes,
            pending_stream_relights=len(self._stream_relight_queue),
            pending_stream_remeshes=len(self._stream_remesh_queue),
            visible_sections=self.visible_sections,
            completed_gpu_uploads=self._completed_gpu_uploads,
            dirty_chunks=self._dirty_chunk_sample,
            pending_saves=self._streamer.pending_save_count,
        )

    def get_block(self, x: int, y: int, z: int) -> int:
        return self._streamer.get_block(x, y, z)

    def is_solid_block(self, x: int, y: int, z: int) -> bool:
        if y < 0:
            return True
        if y >= CHUNK_HEIGHT:
            return False
        chunk_x, _ = split_world_axis(x)
        chunk_z, _ = split_world_axis(z)
        if self._streamer.get_chunk(ChunkCoord(chunk_x, chunk_z)) is None:
            return True
        return self._registry.by_id(self.get_block(x, y, z)).is_solid

    def ensure_collision_area_loaded(self, x: float, z: float, radius: float) -> None:
        for coord in collision_chunk_footprint(x, z, radius):
            if self._streamer.get_chunk(coord) is not None:
                continue
            self._upload_chunk_sync(self._streamer.prime(coord))

    def _create_emergency_spawn(self, x: int, z: int) -> tuple[float, float, float]:
        self.ensure_collision_area_loaded(float(x) + 0.5, float(z) + 0.5, 0.0)
        surface = min(max(self._generator.height_at(x, z), 2), CHUNK_HEIGHT - 2)
        support_y = next(
            (
                y
                for y in range(surface - 1, -1, -1)
                if self._registry.by_id(self.get_block(x, y, z)).is_solid
            ),
            0,
        )
        if not self._registry.by_id(self.get_block(x, support_y, z)).is_solid:
            self.set_block((x, support_y, z), 1)
        spawn_y = min(support_y + 1, CHUNK_HEIGHT - 2)
        self.set_block((x, spawn_y, z), 0)
        self.set_block((x, spawn_y + 1, z), 0)
        return float(x) + 0.5, float(spawn_y), float(z) + 0.5

    def terrain_height_at(self, x: float, z: float) -> float:
        return float(self._generator.height_at(math.floor(x), math.floor(z)))

    def raycast(
        self,
        origin: tuple[float, float, float],
        direction: tuple[float, float, float],
        max_distance: float = 6.0,
    ) -> RaycastHit | None:
        def skip_fluid(block_id: int) -> bool:
            return self._registry.by_id(block_id).is_fluid

        return voxel_raycast(self.get_block, origin, direction, max_distance, skip_block=skip_fluid)

    def set_block(self, block: tuple[int, int, int], block_id: int) -> bool:
        previous_id = self.get_block(*block)
        if block_id == WATER_BLOCK_ID:
            changed = self._streamer.set_fluid(*block, block_id, FLUID_MAX_LEVEL)
        else:
            changed = self._streamer.set_block(*block, block_id)
        if not changed:
            return False
        self._activate_fluid_neighborhood(
            (
                ChunkCoord(
                    split_world_axis(block[0])[0],
                    split_world_axis(block[2])[0],
                ),
            )
        )
        self._remesh_around(block, previous_id, block_id)
        return True

    def update(self, delta_time: float) -> None:
        if self.day_cycle_seconds > 0.0:
            self.time_of_day = (self.time_of_day + delta_time / self.day_cycle_seconds) % 1.0
        self.animation_time += delta_time
        self._fluid_accumulator += delta_time
        if self._fluid_accumulator < 0.2:
            return
        self._fluid_accumulator %= 0.2
        chunks = self._streamer.loaded_chunks()
        if not chunks or not self._fluid_active_chunks:
            return
        chunk_by_coord = {c.coord: c for c in chunks}
        self._fluid_active_chunks.intersection_update(chunk_by_coord)
        dirty_coords: set[ChunkCoord] = set()
        next_active: set[ChunkCoord] = set()
        for coord in tuple(self._fluid_active_chunks):
            chunk = chunk_by_coord[coord]
            cx, cz = chunk.coord.x, chunk.coord.z
            neighbors = {}
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = chunk_by_coord.get(ChunkCoord(cx + dx, cz + dz))
                if nb is not None:
                    neighbors[(dx, dz)] = nb
            result = simulate_water_step(chunk, neighbors or None)
            if result.changed:
                dirty_coords.add(chunk.coord)
                next_active.add(chunk.coord)
            for dx, dz in result.neighbor_keys:
                nb_coord = ChunkCoord(cx + dx, cz + dz)
                if nb_coord in chunk_by_coord:
                    dirty_coords.add(nb_coord)
                    next_active.add(nb_coord)
        self._fluid_active_chunks = next_active
        if dirty_coords:
            affected_chunks = {
                coord: chunk_by_coord[coord] for coord in dirty_coords if coord in chunk_by_coord
            }
            for affected in self._relight_neighborhood(tuple(affected_chunks)):
                affected_chunks[affected.coord] = affected
            for affected in affected_chunks.values():
                self._schedule_chunk(affected)

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

    def set_render_distance(self, render_distance: int) -> bool:
        return self._streamer.set_render_distance(render_distance)

    def enable_streaming_stage_profiling(self, enabled: bool = True) -> None:
        self._streaming_stage_profiling = enabled
        self.last_streaming_stage_sample = StreamingStageSample()

    def update_streaming(
        self,
        center: ChunkCoord,
        *,
        collision_chunks: frozenset[ChunkCoord] | None = None,
    ) -> None:
        profiling = self._streaming_stage_profiling
        streamer_ms = 0.0
        integration_ms = 0.0
        if not self.remote_mode:
            self._refresh_stream_work_horizon(center)
            chunk_budget = frame_budget(self.uploads_per_frame)
            stage_start = perf_counter() if profiling else 0.0
            batch = self._streamer.update(
                center,
                max_completed=chunk_budget,
                max_submitted=chunk_budget,
            )
            if profiling:
                streamer_ms = (perf_counter() - stage_start) * 1000.0
                stage_start = perf_counter()
            self._remove_chunks(batch.unloaded)
            for chunk in batch.loaded:
                if self._stream_relight_relevant(chunk.coord):
                    self._stream_relight_queue[chunk.coord] = None
            for coord in batch.unloaded:
                if self._stream_relight_relevant(coord):
                    self._stream_relight_queue[coord] = None
            self._queue_loaded_chunk_boundaries(batch.loaded)
            self._activate_fluid_neighborhood(chunk.coord for chunk in batch.loaded)
            if profiling:
                integration_ms = (perf_counter() - stage_start) * 1000.0
        stage_start = perf_counter() if profiling else 0.0
        relight_work = self._flush_stream_relight_queue(
            center,
            collision_chunks=collision_chunks,
        )
        relight_ms = (perf_counter() - stage_start) * 1000.0 if profiling else 0.0
        stage_start = perf_counter() if profiling else 0.0
        remesh_budget = self.mesh_uploads_per_frame
        if relight_work:
            remesh_budget = max(1, remesh_budget // 2)
        self._flush_stream_remesh_queue(
            center,
            collision_chunks=collision_chunks,
            limit=remesh_budget,
        )
        if profiling:
            self.last_streaming_stage_sample = StreamingStageSample(
                streamer_ms=streamer_ms,
                integration_ms=integration_ms,
                relight_ms=relight_ms,
                remesh_ms=(perf_counter() - stage_start) * 1000.0,
            )

    def _refresh_stream_work_horizon(self, center: ChunkCoord) -> None:
        render_distance = self._streamer.render_distance
        radius = render_distance
        if self.fog_enabled:
            radius = min(
                render_distance,
                max(0, int(self.fog_end // SECTION_SIZE) + 1),
            )
        mesh_active = {
            ChunkCoord(center.x + dx, center.z + dz)
            for dx in range(-radius, radius + 1)
            for dz in range(-radius, radius + 1)
            if not self.fog_enabled or self._chunk_may_reach_fog_horizon(dx, dz)
        }
        relight_radius = radius if not self.fog_enabled else min(radius, 1)
        relight_active = {
            ChunkCoord(center.x + dx, center.z + dz)
            for dx in range(-relight_radius, relight_radius + 1)
            for dz in range(-relight_radius, relight_radius + 1)
        }
        if (
            mesh_active == self._stream_mesh_active
            and relight_active == self._stream_relight_active
        ):
            return

        entered_mesh = mesh_active - self._stream_mesh_active
        entered_relight = relight_active - self._stream_relight_active
        self._stream_mesh_active = mesh_active
        self._stream_relight_active = relight_active
        for coord in tuple(self._stream_remesh_queue):
            if coord not in mesh_active:
                self._stream_remesh_queue.pop(coord, None)
        for coord in tuple(self._stream_relight_queue):
            if not self._stream_relight_relevant(coord):
                self._stream_relight_queue.pop(coord, None)
        for coord in entered_mesh:
            chunk = self._streamer.get_chunk(coord)
            if chunk is None:
                continue
            self._stream_remesh_queue[coord] = None
        for coord in entered_relight:
            if self._streamer.get_chunk(coord) is not None:
                self._stream_relight_queue[coord] = None

    def _chunk_may_reach_fog_horizon(self, dx: int, dz: int) -> bool:
        gap_x = max(0, abs(dx) - 1) * SECTION_SIZE
        gap_z = max(0, abs(dz) - 1) * SECTION_SIZE
        return gap_x * gap_x + gap_z * gap_z <= self.fog_end * self.fog_end

    def _stream_relight_relevant(self, coord: ChunkCoord) -> bool:
        return any(
            ChunkCoord(coord.x + dx, coord.z + dz) in self._stream_relight_active
            for dx in (-1, 0, 1)
            for dz in (-1, 0, 1)
        )

    def _queue_loaded_chunk_boundaries(self, chunks: Iterable[Chunk]) -> None:
        affected_chunks = {chunk.coord: chunk for chunk in chunks}
        for loaded_chunk in chunks:
            for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nc = ChunkCoord(loaded_chunk.coord.x + dx, loaded_chunk.coord.z + dz)
                if nc not in affected_chunks:
                    neighbor = self._streamer.get_chunk(nc)
                    if neighbor is not None:
                        affected_chunks[nc] = neighbor
        self._queue_stream_remesh(affected_chunks.values())

    def _activate_fluid_neighborhood(self, coordinates: Iterable[ChunkCoord]) -> None:
        candidates: set[ChunkCoord] = set()
        for coord in coordinates:
            candidates.add(coord)
            for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                candidates.add(ChunkCoord(coord.x + dx, coord.z + dz))
        for coord in candidates:
            chunk = self._streamer.get_chunk(coord)
            if chunk is not None and chunk_contains_water(chunk):
                self._fluid_active_chunks.add(coord)

    def _flush_stream_relight_queue(
        self,
        center: ChunkCoord,
        *,
        collision_chunks: frozenset[ChunkCoord] | None = None,
    ) -> bool:
        centers = drain_grouped_priority_keys(
            self._stream_relight_queue,
            self.uploads_per_frame,
            lambda coord: chunk_distance((coord.x, coord.z), (center.x, center.z)),
            lambda coord: streaming_priority(
                0,
                chunk_visible(self._streaming_frustum, (coord.x, coord.z)),
                None if collision_chunks is None else coord in collision_chunks,
            )[1:],
        )
        if centers:
            self._queue_stream_remesh(self._relight_neighborhood(centers))
        return bool(centers)

    def _queue_stream_remesh(self, chunks: Iterable[Chunk]) -> None:
        for chunk in chunks:
            if chunk.coord in self._stream_mesh_active:
                self._stream_remesh_queue[chunk.coord] = None

    def _flush_stream_remesh_queue(
        self,
        center: ChunkCoord,
        *,
        collision_chunks: frozenset[ChunkCoord] | None = None,
        limit: int | None = None,
    ) -> None:
        available_slots = max(
            0,
            self.mesh_worker.max_pending_count - self.mesh_worker.pending_count,
        )
        budget = min(
            self.mesh_uploads_per_frame if limit is None else limit,
            available_slots,
        )
        if budget <= 0:
            return
        eligible = {
            coord: None
            for coord in self._stream_remesh_queue
            if not self.mesh_worker.is_chunk_pending(coord) and self._stream_mesh_ready(coord)
        }
        for key in drain_grouped_priority_keys(
            eligible,
            budget,
            lambda coord: chunk_distance((coord.x, coord.z), (center.x, center.z)),
            lambda coord: streaming_priority(
                0,
                chunk_visible(
                    self._streaming_frustum,
                    (coord.x, coord.z),
                ),
                None if collision_chunks is None else coord in collision_chunks,
            )[1:],
        ):
            self._stream_remesh_queue.pop(key, None)
            chunk = self._streamer.get_chunk(key)
            if chunk is not None:
                self._schedule_chunk(chunk)

    def _stream_mesh_ready(self, coord: ChunkCoord) -> bool:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = ChunkCoord(coord.x + dx, coord.z + dz)
            if self._streamer.get_chunk(neighbor) is None and self._streamer.expects_chunk(
                neighbor
            ):
                return False
        return True

    def render(
        self,
        camera: FirstPersonCamera,
        width: int,
        height: int,
        fov: float,
        shadow_caster: Callable[[np.ndarray], object] | None = None,
        transparent_underlay: Callable[[np.ndarray], object] | None = None,
    ) -> None:
        if self.shader.program is None:
            return
        matrix = camera_matrix(camera, max(width, 1) / max(height, 1), fov)

        opaque_updates: dict[SectionCoord, MeshData | None] = {}
        water_updates: dict[SectionCoord, MeshData | None] = {}
        for completed in self.mesh_worker.poll(self.mesh_uploads_per_frame):
            if self._streamer.get_chunk(completed.key.chunk) is None:
                continue
            opaque_updates[completed.key] = completed.mesh
            water_updates[completed.key] = completed.transparent_mesh
        self._completed_gpu_uploads += self.mesh_cache.apply(opaque_updates)
        self._completed_gpu_uploads += self.water_mesh_cache.apply(water_updates)

        light_matrix = (
            sun_light_matrix(
                camera.position,
                map_size=self.shadow_map.size,
                direction=self.light_direction,
            )
            if self.shadow_map is not None
            else np.identity(4, dtype=np.float32)
        )
        if self.shadow_map is not None:
            self._render_shadow_depth(light_matrix, width, height, shadow_caster)

        camera_uniform = cast("moderngl.Uniform", self.shader.program["camera_matrix"])
        texture_uniform = cast("moderngl.Uniform", self.shader.program["texture_atlas"])
        camera_position_uniform = cast("moderngl.Uniform", self.shader.program["camera_position"])
        day_tint_uniform = cast("moderngl.Uniform", self.shader.program["day_tint"])
        daylight_uniform = cast("moderngl.Uniform", self.shader.program["daylight"])
        fog_color_uniform = cast("moderngl.Uniform", self.shader.program["fog_color"])
        fog_start_uniform = cast("moderngl.Uniform", self.shader.program["fog_start"])
        fog_end_uniform = cast("moderngl.Uniform", self.shader.program["fog_end"])
        fog_enabled_uniform = cast("moderngl.Uniform", self.shader.program["fog_enabled"])
        cast("moderngl.Uniform", self.shader.program["shadow_matrix"]).write(
            light_matrix.T.astype("f4").tobytes()
        )
        cast(
            "moderngl.Uniform", self.shader.program["light_direction"]
        ).value = self.light_direction
        cast("moderngl.Uniform", self.shader.program["shadows_enabled"]).value = int(
            self.shadow_map is not None
        )
        cast("moderngl.Uniform", self.shader.program["shadow_bias"]).value = self.shadow_bias
        active_shadow_texture = (
            self.shadow_map.texture if self.shadow_map is not None else self._neutral_shadow_texture
        )
        cast("moderngl.Uniform", self.shader.program["shadow_texel_size"]).value = (
            1.0 / active_shadow_texture.width
        )
        cast(
            "moderngl.Uniform", self.shader.program["tile_uv_margin"]
        ).value = self.atlas_tile_margin
        cast("moderngl.Uniform", self.shader.program["grass_top_rect"]).value = self.atlas_uvs[
            "minecraft:block/grass_block_top"
        ]
        cast("moderngl.Uniform", self.shader.program["terrain_variation_enabled"]).value = int(
            self.linear_texture_minification
        )
        cast(
            "moderngl.Uniform", self.shader.program["vegetation_wind_time"]
        ).value = self.animation_time
        cast("moderngl.Uniform", self.shader.program["vegetation_wind_enabled"]).value = int(
            self.vegetation_wind_enabled
        )
        cast("moderngl.Uniform", self.shader.program["shadow_map"]).value = 1
        camera_uniform.write(matrix.T.astype("f4").tobytes())
        self.texture.use(0)
        active_shadow_texture.use(1)
        bind_material_atlas_textures(self.material_atlas_textures)
        texture_uniform.value = 0
        camera_position_uniform.value = camera.position
        daylight_uniform.value = self.daylight
        day_tint_uniform.value = (
            0.55 + 0.45 * self.daylight,
            0.62 + 0.38 * self.daylight,
            0.78 + 0.22 * self.daylight,
        )
        underwater = self._registry.by_id(
            self.get_block(
                int(np.floor(camera.x)),
                int(np.floor(camera.y)),
                int(np.floor(camera.z)),
            )
        ).is_fluid
        active_fog_color = (0.065, 0.21, 0.29) if underwater else self.clear_color[:3]
        active_fog_start = 0.0 if underwater else self.fog_start
        active_fog_end = 18.0 if underwater else self.fog_end
        fog_color_uniform.value = active_fog_color
        fog_start_uniform.value = active_fog_start
        fog_end_uniform.value = active_fog_end
        fog_enabled_uniform.value = int(self.fog_enabled)
        origin_uniform = cast("moderngl.Uniform", self.shader.program["section_origin"])
        self.visible_sections = 0
        self.draw_calls = 0
        self.face_count = 0
        self.triangle_count = 0
        frustum = Frustum(matrix)
        self._streaming_frustum = frustum
        for _key, gpu_mesh in self.mesh_cache.items():
            if not frustum.intersects(gpu_mesh.minimum, gpu_mesh.maximum):
                continue
            if self.fog_enabled and _outside_fog_range(
                camera.position,
                gpu_mesh.minimum,
                gpu_mesh.maximum,
                active_fog_end,
            ):
                continue
            origin_uniform.value = gpu_mesh.origin
            gpu_mesh.vertex_array.render(moderngl.TRIANGLES)
            self.visible_sections += gpu_mesh.section_count
            self.draw_calls += 1
            self.face_count += gpu_mesh.data.face_count
            self.triangle_count += gpu_mesh.data.triangle_count
        if transparent_underlay is not None:
            transparent_underlay(light_matrix)
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

    @property
    def active_atlas(self) -> GeneratedAtlas:
        return self._atlas

    def apply_texture_pack(self, atlas: GeneratedAtlas) -> None:
        """Hot-swap the block texture atlas and remesh all loaded chunks."""
        old_texture = self.texture
        self.texture = self.context.texture((atlas.width, atlas.height), 4, atlas.pixels)
        _configure_block_texture(
            self.texture,
            linear_minification=self.linear_texture_minification,
        )
        self._atlas = atlas
        old_texture.release()

        self.atlas_uvs = atlas.uvs
        self.atlas_tile_margin = _atlas_tile_margin(atlas)
        if self._meshing_backend == "thread":
            self.mesh_worker.texture_uvs = atlas.uvs
        else:
            self.mesh_worker.close()
            self.mesh_worker = SectionMeshWorker(
                self._registry,
                atlas.uvs,
                workers=self._meshing_workers,
                backend=cast(Literal["thread", "process"], self._meshing_backend),
            )

        self.water_mesh_cache.release()
        self.mesh_cache.release()
        assert self.shader.program is not None
        assert self.water_shader.program is not None
        self.mesh_cache = SectionMeshCache(
            self.context,
            self.shader.program,
            self.shadow_shader.program if self.shadow_map is not None else None,
            batch_chunks=self.opaque_batch_chunks,
            batch_vertical_sections=True,
        )
        self.water_mesh_cache = SectionMeshCache(
            self.context,
            self.water_shader.program,
            wind_motion=False,
            shoreline_factor=True,
        )
        self._remesh_all()

    def apply_texture_minification(self, linear_minification: bool) -> None:
        """Apply the active quality profile's sampler choice without remeshing."""
        self.linear_texture_minification = linear_minification
        _configure_block_texture(
            self.texture,
            linear_minification=linear_minification,
        )
        for material_texture in self.material_atlas_textures.values():
            _configure_block_texture(
                material_texture.texture,
                linear_minification=linear_minification,
            )

    def apply_material_quality(self, material_quality: str, resource_pack_path: str = "") -> None:
        """Hot-swap the material quality profile and rebuild the chunk shader path."""
        release_material_atlas_textures(self.material_atlas_textures)
        old_shader = self.shader
        self.material_pipeline = resolve_material_pipeline_from_graphics(material_quality)
        self.material_bundle = None
        material_roles: Iterable[MaterialMapRole] = ()
        if self.material_pipeline.build_material_bundle:
            pack_path = Path(resource_pack_path) if resource_pack_path else None
            material_pack_path = pack_path or resource_path("resource_packs/default")
            self.material_bundle = load_material_atlas_bundle(material_pack_path, self._atlas)
            material_roles = self.material_bundle.materials.keys()
        self.material_shader_setup = build_material_shader_setup(
            self.material_pipeline,
            material_roles,
        )
        self.material_shader_wiring = build_material_shader_runtime_wiring(
            self.material_shader_setup,
            self._shader_root,
        )
        self.material_shader_activation = activate_material_shader(
            self.context, self.material_shader_wiring
        )
        self.material_atlas_textures = build_activated_material_atlas_textures(
            self.context,
            self.material_shader_activation,
            self.material_bundle,
            linear_minification=self.linear_texture_minification,
        )
        apply_material_sampler_bindings(self.material_shader_activation)
        if self.material_shader_activation is not None:
            self.shader = resolve_chunk_draw_shader(old_shader, self.material_shader_activation)
        else:
            self.shader = ShaderProgram(
                self.context, ShaderFiles.from_directory(self._shader_root, "chunk_opaque")
            )
        old_shader.release()
        if self.shader.program is None:
            raise RuntimeError("Chunk shader failed to compile")
        self.mesh_cache.release()
        self.mesh_cache = SectionMeshCache(
            self.context,
            self.shader.program,
            self.shadow_shader.program if self.shadow_map is not None else None,
            batch_chunks=self.opaque_batch_chunks,
            batch_vertical_sections=True,
        )
        self._remesh_all()

    def release(self) -> None:
        self.mesh_worker.close()
        self._streamer.close()
        self.highlight.release()
        self.water_mesh_cache.release()
        self.mesh_cache.release()
        self.texture.release()
        self.shader.release()
        release_material_atlas_textures(self.material_atlas_textures)
        if (
            self.material_shader_activation is not None
            and self.material_shader_activation.shader is not self.shader
        ):
            self.material_shader_activation.shader.release()
        self.water_shader.release()
        self.shadow_shader.release()
        self._neutral_shadow_texture.release()
        if self.shadow_map is not None:
            self.shadow_map.release()

    def autosave(self) -> int:
        self._storage.ensure_world(name=self.world_name, seed=self.seed_text)
        return self._streamer.save_dirty()

    def install_remote_chunk(self, chunk: Chunk) -> None:
        self._streamer.install_chunk(chunk)
        self._activate_fluid_neighborhood((chunk.coord,))
        affected_chunks = {chunk.coord: chunk}
        for affected in self._relight_neighborhood((chunk.coord,)):
            affected_chunks[affected.coord] = affected
        for affected in affected_chunks.values():
            self._schedule_chunk(affected)

    def rebuild_loaded_chunk_meshes_sync(self, coordinates: Iterable[ChunkCoord]) -> int:
        """Rebuild selected loaded chunks immediately for deterministic tooling."""

        rebuilt = 0
        for coord in set(coordinates):
            chunk = self._streamer.get_chunk(coord)
            if chunk is None:
                continue
            self.mesh_worker.invalidate_chunk(coord.x, coord.z)
            self._upload_chunk_sync(chunk)
            rebuilt += 1
        return rebuilt

    def enable_remote_mode(self) -> None:
        self.remote_mode = True

    def _upload_chunk_sync(self, chunk: Chunk) -> None:
        opaque_updates: dict[SectionCoord, MeshData | None] = {}
        water_updates: dict[SectionCoord, MeshData | None] = {}
        for section_y, section in enumerate(chunk.sections):
            key = SectionCoord(chunk.coord.x, section_y, chunk.coord.z)
            if not np.any(section.blocks):
                opaque_updates[key] = None
                water_updates[key] = None
                continue
            mesh, water_mesh = self._build_mesh(key, section)
            opaque_updates[key] = mesh
            water_updates[key] = water_mesh
        self._completed_gpu_uploads += self.mesh_cache.apply(opaque_updates)
        self._completed_gpu_uploads += self.water_mesh_cache.apply(water_updates)

    def _remove_chunks(self, coords: Iterable[ChunkCoord]) -> None:
        unloaded = tuple(coords)
        if not unloaded:
            return
        for coord in unloaded:
            self._fluid_active_chunks.discard(coord)
            self._stream_relight_queue.pop(coord, None)
            self._stream_remesh_queue.pop(coord, None)
            self.mesh_worker.invalidate_chunk(coord.x, coord.z)
        keys = tuple(
            SectionCoord(coord.x, section_y, coord.z)
            for coord in unloaded
            for section_y in range(CHUNK_HEIGHT // SECTION_SIZE)
        )
        self.mesh_cache.remove_many(iter(keys))
        self.water_mesh_cache.remove_many(iter(keys))

    def _remesh_around(self, block: tuple[int, int, int], previous_id: int, new_id: int) -> None:
        x, y, z = block
        prev_def = self._registry.by_id(previous_id)
        new_def = self._registry.by_id(new_id)

        needs_relight = (
            prev_def.emits_light != new_def.emits_light
            or prev_def.is_transparent != new_def.is_transparent
            or prev_def.is_fluid != new_def.is_fluid
        )

        if needs_relight:
            chunk_x = x // SECTION_SIZE
            chunk_z = z // SECTION_SIZE
            chunk = self._streamer.get_chunk(ChunkCoord(chunk_x, chunk_z))
            if chunk is not None:
                chunks_to_schedule = {c.coord: c for c in self._relight_neighborhood([chunk.coord])}
                for c in chunks_to_schedule.values():
                    self._schedule_chunk(c)
            return

        section_coords = {SectionCoord(x // SECTION_SIZE, y // SECTION_SIZE, z // SECTION_SIZE)}
        if x % SECTION_SIZE == 0:
            section_coords.add(
                SectionCoord((x - 1) // SECTION_SIZE, y // SECTION_SIZE, z // SECTION_SIZE)
            )
        elif x % SECTION_SIZE == SECTION_SIZE - 1:
            section_coords.add(
                SectionCoord((x + 1) // SECTION_SIZE, y // SECTION_SIZE, z // SECTION_SIZE)
            )
        if y % SECTION_SIZE == 0 and y > 0:
            section_coords.add(
                SectionCoord(x // SECTION_SIZE, (y - 1) // SECTION_SIZE, z // SECTION_SIZE)
            )
        elif y % SECTION_SIZE == SECTION_SIZE - 1 and y < CHUNK_HEIGHT - 1:
            section_coords.add(
                SectionCoord(x // SECTION_SIZE, (y + 1) // SECTION_SIZE, z // SECTION_SIZE)
            )
        if z % SECTION_SIZE == 0:
            section_coords.add(
                SectionCoord(x // SECTION_SIZE, y // SECTION_SIZE, (z - 1) // SECTION_SIZE)
            )
        elif z % SECTION_SIZE == SECTION_SIZE - 1:
            section_coords.add(
                SectionCoord(x // SECTION_SIZE, y // SECTION_SIZE, (z + 1) // SECTION_SIZE)
            )

        for key in section_coords:
            self._schedule_section(key)

    def _relight_neighborhood(self, centers: Iterable[ChunkCoord]) -> tuple[Chunk, ...]:
        coordinates = {
            ChunkCoord(center.x + dx, center.z + dz)
            for center in centers
            for dx in (-1, 0, 1)
            for dz in (-1, 0, 1)
        }
        chunks = tuple(
            chunk
            for coord in sorted(coordinates, key=lambda item: (item.x, item.z))
            if (chunk := self._streamer.get_chunk(coord)) is not None
        )
        return relight_chunks(chunks, self._registry)

    def _schedule_chunk(self, chunk: Chunk) -> None:
        tasks = {}
        empty_keys: list[SectionCoord] = []
        for section_y, section in enumerate(chunk.sections):
            key = SectionCoord(chunk.coord.x, section_y, chunk.coord.z)
            if not np.any(section.blocks):
                empty_keys.append(key)
                continue
            tasks[key] = self._build_neighborhood(key)

        self.mesh_cache.remove_many(empty_keys)
        self.water_mesh_cache.remove_many(empty_keys)

        if tasks:
            self.mesh_worker.submit_chunk(
                chunk.coord,
                tasks,
                greedy=self.greedy_meshing,
                smooth_lighting=self.smooth_lighting,
                ambient_occlusion=self.ambient_occlusion,
            )

    def _schedule_section(self, key: SectionCoord, chunk: Chunk | None = None) -> None:
        if chunk is None:
            chunk = self._streamer.get_chunk(ChunkCoord(key.x, key.z))
        if chunk is None or not (0 <= key.y < len(chunk.sections)):
            return
        section = chunk.sections[key.y]
        if not np.any(section.blocks):
            self.mesh_cache.remove(key)
            self.water_mesh_cache.remove(key)
            return
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
                self._registry,
                self.atlas_uvs,
                smooth_lighting=self.smooth_lighting,
                ambient_occlusion=self.ambient_occlusion,
            ),
            build_water_mesh(neighborhood, self._registry, self.atlas_uvs),
        )

    def _build_neighborhood(self, key: SectionCoord) -> MeshingNeighborhood:
        origin = (
            key.x * SECTION_SIZE - HALO_RADIUS,
            key.y * SECTION_SIZE - HALO_RADIUS,
            key.z * SECTION_SIZE - HALO_RADIUS,
        )
        blocks, sky_light, block_light, metadata = self._streamer.snapshot_region(
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
        cast("moderngl.Uniform", program["sky_color"]).value = self.clear_color[:3]
        cast("moderngl.Uniform", program["water_detail_enabled"]).value = int(
            self.water_detail_enabled
        )
        origin_uniform = cast("moderngl.Uniform", program["section_origin"])
        visible: list[tuple[float, SectionCoord, GpuSectionMesh]] = []
        frustum = Frustum(matrix)
        for key, gpu_mesh in self.water_mesh_cache.items():
            if not frustum.intersects(gpu_mesh.minimum, gpu_mesh.maximum):
                continue
            if self.fog_enabled and _outside_fog_range(
                camera.position,
                gpu_mesh.minimum,
                gpu_mesh.maximum,
                fog_end,
            ):
                continue
            center = tuple(
                (gpu_mesh.minimum[index] + gpu_mesh.maximum[index]) * 0.5 for index in range(3)
            )
            distance = sum((center[i] - camera.position[i]) ** 2 for i in range(3))
            visible.append((distance, key, gpu_mesh))

        self.context.enable(moderngl.BLEND)
        self.context.disable(moderngl.CULL_FACE)
        self.context.depth_mask = False  # pyright: ignore[reportAttributeAccessIssue]
        self.context.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        for _distance, _key, gpu_mesh in sorted(visible, reverse=True, key=lambda item: item[0]):
            origin_uniform.value = gpu_mesh.origin
            gpu_mesh.vertex_array.render(moderngl.TRIANGLES)
            self.draw_calls += 1
            self.face_count += gpu_mesh.data.face_count
            self.triangle_count += gpu_mesh.data.triangle_count
        self.context.depth_mask = True  # pyright: ignore[reportAttributeAccessIssue]
        self.context.disable(moderngl.BLEND)
        self.context.enable(moderngl.CULL_FACE)

    def _render_shadow_depth(
        self,
        light_matrix: np.ndarray,
        width: int,
        height: int,
        shadow_caster: Callable[[np.ndarray], object] | None,
    ) -> None:
        shadow_map = self.shadow_map
        program = self.shadow_shader.program
        if shadow_map is None or program is None:
            return
        previous_framebuffer = self.context.fbo
        previous_viewport = self.context.viewport
        shadow_map.framebuffer.use()
        self.context.viewport = (0, 0, shadow_map.size, shadow_map.size)
        self.context.clear(depth=1.0)
        self.context.disable(moderngl.CULL_FACE)
        self.texture.use(0)
        cast("moderngl.Uniform", program["texture_atlas"]).value = 0
        cast("moderngl.Uniform", program["tile_uv_margin"]).value = self.atlas_tile_margin
        cast("moderngl.Uniform", program["vegetation_wind_time"]).value = self.animation_time
        cast("moderngl.Uniform", program["vegetation_wind_enabled"]).value = int(
            self.vegetation_wind_enabled
        )
        cast("moderngl.Uniform", program["light_matrix"]).write(
            light_matrix.T.astype("f4").tobytes()
        )
        origin_uniform = cast("moderngl.Uniform", program["section_origin"])
        for _key, gpu_mesh in self.mesh_cache.items():
            if gpu_mesh.depth_vertex_array is None:
                continue
            origin_uniform.value = gpu_mesh.origin
            gpu_mesh.depth_vertex_array.render(moderngl.TRIANGLES)
        if shadow_caster is not None:
            shadow_caster(light_matrix)
        self.context.cull_face = "back"
        previous_framebuffer.use()
        self.context.viewport = previous_viewport
        self.context.enable(moderngl.CULL_FACE)

    def _remesh_all(self) -> None:
        for chunk in self._streamer.loaded_chunks():
            self._schedule_chunk(chunk)
