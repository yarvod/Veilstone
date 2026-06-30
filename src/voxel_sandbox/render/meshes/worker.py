from __future__ import annotations

from concurrent.futures import Executor, Future, ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Literal

from voxel_sandbox.domain.blocks import BlockDef, BlockRegistry
from voxel_sandbox.engine.chunks import ChunkCoord, SectionCoord
from voxel_sandbox.render.meshes.data import MeshData
from voxel_sandbox.render.meshes.greedy import build_greedy_mesh
from voxel_sandbox.render.meshes.neighborhood import MeshingNeighborhood
from voxel_sandbox.render.meshes.visible_faces import build_visible_face_mesh
from voxel_sandbox.render.meshes.water import build_water_mesh


@dataclass(frozen=True, slots=True)
class CompletedMesh:
    key: SectionCoord
    revision: int
    mesh: MeshData
    transparent_mesh: MeshData


MeshTask = tuple[SectionCoord, int, MeshingNeighborhood]


class SectionMeshWorker:
    def __init__(
        self,
        registry: BlockRegistry,
        texture_uvs: dict[str, tuple[float, float, float, float]],
        *,
        workers: int,
        backend: Literal["thread", "process"] = "thread",
    ) -> None:
        if workers < 1:
            raise ValueError("At least one meshing worker is required")
        if backend not in {"thread", "process"}:
            raise ValueError(f"Unsupported meshing backend: {backend}")
        self.registry = registry
        self.texture_uvs = texture_uvs
        self._backend = backend
        self._executor: Executor
        if backend == "process":
            self._executor = ProcessPoolExecutor(
                max_workers=workers,
                initializer=_initialize_process_worker,
                initargs=(tuple(registry), texture_uvs),
            )
            _warm_process_pool(self._executor, workers)
        else:
            self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="meshing")
        self._pending: dict[SectionCoord, Future[CompletedMesh]] = {}
        self._pending_chunks: dict[tuple[int, int], Future[tuple[CompletedMesh, ...]]] = {}
        self._revisions: dict[SectionCoord, int] = {}

    @property
    def pending_count(self) -> int:
        return len(self._pending) + len(self._pending_chunks)

    def submit(
        self,
        key: SectionCoord,
        neighborhood: MeshingNeighborhood,
        *,
        greedy: bool,
        smooth_lighting: bool,
        ambient_occlusion: bool,
    ) -> None:
        revision = self._revisions.get(key, 0) + 1
        self._revisions[key] = revision
        previous = self._pending.get(key)
        if previous is not None:
            previous.cancel()
        if self._backend == "process":
            self._pending[key] = self._executor.submit(
                _build_process_mesh,
                key,
                revision,
                neighborhood,
                greedy,
                smooth_lighting,
                ambient_occlusion,
            )
        else:
            self._pending[key] = self._executor.submit(
                self._build,
                key,
                revision,
                neighborhood,
                greedy,
                smooth_lighting,
                ambient_occlusion,
            )

    def submit_chunk(
        self,
        coord: ChunkCoord,
        tasks: dict[SectionCoord, MeshingNeighborhood],
        *,
        greedy: bool,
        smooth_lighting: bool,
        ambient_occlusion: bool,
    ) -> None:
        batch_args: list[MeshTask] = []
        for key, neighborhood in tasks.items():
            revision = self._revisions.get(key, 0) + 1
            self._revisions[key] = revision
            previous = self._pending.get(key)
            if previous is not None:
                previous.cancel()
                del self._pending[key]
            batch_args.append((key, revision, neighborhood))

        previous_chunk = self._pending_chunks.get((coord.x, coord.z))
        if previous_chunk is not None:
            previous_chunk.cancel()

        if self._backend == "process":
            self._pending_chunks[(coord.x, coord.z)] = self._executor.submit(
                _build_chunk_process_mesh,
                tuple(batch_args),
                greedy,
                smooth_lighting,
                ambient_occlusion,
            )
        else:
            self._pending_chunks[(coord.x, coord.z)] = self._executor.submit(
                self._build_chunk,
                tuple(batch_args),
                greedy,
                smooth_lighting,
                ambient_occlusion,
            )

    def poll(self, limit: int) -> tuple[CompletedMesh, ...]:
        completed: list[CompletedMesh] = []
        for key, future in tuple(self._pending.items()):
            if len(completed) >= limit:
                break
            if not future.done():
                continue
            del self._pending[key]
            if future.cancelled():
                continue
            result = future.result()
            if self._revisions.get(key) == result.revision:
                completed.append(result)

        for key, future in tuple(self._pending_chunks.items()):
            if len(completed) >= limit:
                break
            if not future.done():
                continue
            del self._pending_chunks[key]
            if future.cancelled():
                continue
            results = future.result()
            for result in results:
                if self._revisions.get(result.key) == result.revision:
                    completed.append(result)

        return tuple(completed)

    def invalidate_chunk(self, chunk_x: int, chunk_z: int) -> None:
        chunk_future = self._pending_chunks.pop((chunk_x, chunk_z), None)
        if chunk_future is not None:
            chunk_future.cancel()

        for key in tuple(self._revisions):
            if key.x != chunk_x or key.z != chunk_z:
                continue
            self._revisions[key] += 1
            future = self._pending.pop(key, None)
            if future is not None:
                future.cancel()

    def close(self) -> None:
        for future in self._pending.values():
            future.cancel()
        for future in self._pending_chunks.values():
            future.cancel()
        self._executor.shutdown(wait=True, cancel_futures=True)
        self._pending.clear()
        self._pending_chunks.clear()

    def _build(
        self,
        key: SectionCoord,
        revision: int,
        neighborhood: MeshingNeighborhood,
        greedy: bool,
        smooth_lighting: bool,
        ambient_occlusion: bool,
    ) -> CompletedMesh:
        builder = build_greedy_mesh if greedy else build_visible_face_mesh
        mesh = builder(
            neighborhood,
            self.registry,
            self.texture_uvs,
            smooth_lighting=smooth_lighting,
            ambient_occlusion=ambient_occlusion,
        )
        transparent_mesh = build_water_mesh(neighborhood, self.registry, self.texture_uvs)
        return CompletedMesh(key, revision, mesh, transparent_mesh)

    def _build_chunk(
        self,
        tasks: tuple[MeshTask, ...],
        greedy: bool,
        smooth_lighting: bool,
        ambient_occlusion: bool,
    ) -> tuple[CompletedMesh, ...]:
        results: list[CompletedMesh] = []
        for key, revision, neighborhood in tasks:
            results.append(
                self._build(key, revision, neighborhood, greedy, smooth_lighting, ambient_occlusion)
            )
        return tuple(results)


_process_registry: BlockRegistry | None = None
_process_texture_uvs: dict[str, tuple[float, float, float, float]] | None = None


def _initialize_process_worker(
    definitions: tuple[BlockDef, ...],
    texture_uvs: dict[str, tuple[float, float, float, float]],
) -> None:
    global _process_registry, _process_texture_uvs
    _process_registry = BlockRegistry(definitions)
    _process_texture_uvs = texture_uvs


def _build_process_mesh(
    key: SectionCoord,
    revision: int,
    neighborhood: MeshingNeighborhood,
    greedy: bool,
    smooth_lighting: bool,
    ambient_occlusion: bool,
) -> CompletedMesh:
    if _process_registry is None or _process_texture_uvs is None:
        raise RuntimeError("Meshing process worker was not initialized")
    builder = build_greedy_mesh if greedy else build_visible_face_mesh
    mesh = builder(
        neighborhood,
        _process_registry,
        _process_texture_uvs,
        smooth_lighting=smooth_lighting,
        ambient_occlusion=ambient_occlusion,
    )
    transparent_mesh = build_water_mesh(
        neighborhood,
        _process_registry,
        _process_texture_uvs,
    )
    return CompletedMesh(key, revision, mesh, transparent_mesh)


def _build_chunk_process_mesh(
    tasks: tuple[MeshTask, ...],
    greedy: bool,
    smooth_lighting: bool,
    ambient_occlusion: bool,
) -> tuple[CompletedMesh, ...]:
    results: list[CompletedMesh] = []
    for key, revision, neighborhood in tasks:
        results.append(
            _build_process_mesh(
                key, revision, neighborhood, greedy, smooth_lighting, ambient_occlusion
            )
        )
    return tuple(results)


def _warm_process_pool(executor: Executor, workers: int) -> None:
    futures = [executor.submit(_process_ready) for _ in range(workers)]
    for future in futures:
        future.result()


def _process_ready() -> bool:
    return True
